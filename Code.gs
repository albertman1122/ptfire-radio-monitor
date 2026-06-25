var SHEET_ID    = "1moUSz2aIMclgRCQzSs_273x0F4TAdymLtxJbsBYF9dw";
var LOG_SHEET   = "監控紀錄Log";
var ALERT_SHEET = "告警事件記錄";
var VOLTAGE_MIN = 13.0;
var VOLTAGE_MAX = 13.8;
var GEMINI_KEY  = "AQ.Ab8RN6LhkYIegvhqbYFFAP1_Ain6nA1gt2kJywVuM1-KrL73sA";
var GEMINI_URL  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=";

function doGet(e) {
  return HtmlService.createHtmlOutputFromFile("index")
    .setTitle("無線電中繼台電源監控")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function getData() {
  try {
    var ss       = SpreadsheetApp.openById(SHEET_ID);
    var logWs    = ss.getSheetByName(LOG_SHEET);
    var alertWs  = ss.getSheetByName(ALERT_SHEET);
    var logVals  = logWs.getDataRange().getValues();
    var alertVals = alertWs.getDataRange().getValues();

    var hdr      = logVals[0];
    var timeCol  = findCol(hdr, ["時間","time"]);
    var devCol   = findCol(hdr, ["設備","device"]);
    var vCol     = findCol(hdr, ["電壓","voltage"]);

    var rows = logVals.slice(1).filter(function(r){ return r[devCol] && r[vCol]; });

    var devMap = {};
    rows.forEach(function(r) {
      var dev = String(r[devCol]);
      var v   = parseFloat(r[vCol]);
      var t   = r[timeCol] ? String(r[timeCol]) : "";
      if (!dev || isNaN(v)) return;
      if (!devMap[dev]) devMap[dev] = [];
      devMap[dev].push({ t: t, v: v });
    });

    var today = new Date();
    var todayStr = Utilities.formatDate(today, "Asia/Taipei", "yyyy-MM-dd");

    var stations = Object.keys(devMap).map(function(dev) {
      var pts    = devMap[dev];
      var latest = pts[pts.length - 1];
      var v      = latest.v;
      var isAbn  = !(v >= VOLTAGE_MIN && v <= VOLTAGE_MAX);

      var recent = pts.slice(-6).map(function(p){ return p.v; });
      var trend  = "穩定";
      if (recent.length >= 2) {
        var diff = recent[recent.length-1] - recent[0];
        if (diff < -0.3) trend = "下降";
        else if (diff > 0.3) trend = "上升";
      }

      var consec = 0;
      for (var i = pts.length-1; i >= 0; i--) {
        if (!(pts[i].v >= VOLTAGE_MIN && pts[i].v <= VOLTAGE_MAX)) consec++;
        else break;
      }

      var todayPts = pts.filter(function(p){ return p.t.indexOf(todayStr) >= 0; });
      var dayVs    = todayPts.map(function(p){ return p.v; });
      var dayMax   = dayVs.length ? Math.max.apply(null, dayVs).toFixed(1) : v.toFixed(1);
      var dayMin   = dayVs.length ? Math.min.apply(null, dayVs).toFixed(1) : v.toFixed(1);

      return {
        name:       dev,
        voltage:    v,
        status:     isAbn ? "abnormal" : "normal",
        trend:      trend,
        lastTime:   latest.t,
        consecutive: consec,
        dayMax:     dayMax,
        dayMin:     dayMin,
        chart:      pts.slice(-144).map(function(p){ return { t: p.t, v: p.v }; })
      };
    });

    var aHdr    = alertVals[0];
    var aDevCol = findCol(aHdr, ["設備","device"]);
    var aTypCol = findCol(aHdr, ["異常類型","type"]);
    var aValCol = findCol(aHdr, ["電壓值","value","電壓"]);
    var aTmCol  = findCol(aHdr, ["告警時間","最新記錄時間","記錄時間","time"]);
    var aDiagCol = findCol(aHdr, ["診斷","diagnosis","ai"]);

    var alerts = alertVals.slice(1)
      .filter(function(r){ return r[aDevCol]; })
      .slice(-8).reverse()
      .map(function(r, i) {
        return {
          idx:       i,
          device:    String(r[aDevCol] || ""),
          type:      String(r[aTypCol] || ""),
          value:     String(r[aValCol] || ""),
          time:      String(r[aTmCol]  || ""),
          diagnosis: aDiagCol >= 0 ? String(r[aDiagCol] || "") : ""
        };
      });

    return JSON.stringify({
      ok:         true,
      stations:   stations,
      alerts:     alerts,
      updated:    Utilities.formatDate(new Date(), "Asia/Taipei", "yyyy-MM-dd HH:mm:ss"),
      voltageMin: VOLTAGE_MIN,
      voltageMax: VOLTAGE_MAX
    });
  } catch(e) {
    return JSON.stringify({ ok: false, error: e.toString() });
  }
}

function getAlertDiagnosis(alertIdx) {
  try {
    var raw  = getData();
    var data = JSON.parse(raw);
    if (!data.ok) return JSON.stringify({ ok: false, error: data.error });

    var alert = data.alerts[alertIdx];
    if (!alert) return JSON.stringify({ ok: false, error: "找不到告警記錄" });

    var ss      = SpreadsheetApp.openById(SHEET_ID);
    var logWs   = ss.getSheetByName(LOG_SHEET);
    var logVals = logWs.getDataRange().getValues();
    var hdr     = logVals[0];
    var devCol  = findCol(hdr, ["設備","device"]);
    var vCol    = findCol(hdr, ["電壓","voltage"]);
    var tCol    = findCol(hdr, ["時間","time"]);

    var history = logVals.slice(1)
      .filter(function(r){ return String(r[devCol]) === alert.device && r[vCol]; })
      .slice(-20)
      .map(function(r, i){ return { 序號: i+1, 時間: String(r[tCol]), 電壓: parseFloat(r[vCol]) }; });

    var recent  = history.slice(-6).map(function(h){ return h["電壓"]; });
    var trend   = recent.length >= 2 && recent[recent.length-1] < recent[0] ? "下降" : "上升";
    var rate    = recent.length >= 2 ? Math.abs(recent[recent.length-1] - recent[0]) / recent.length : 0;

    var latestTime = history.length ? history[history.length-1]["時間"] : alert.time;
    var hour = 12;
    var m = latestTime.match(/(\d{2}):\d{2}/);
    if (m) hour = parseInt(m[1]);
    var isNight  = hour >= 18 || hour < 6;
    var timeCtx  = isNight ? "（當前時間為晚間，正常放電期間）" : "（當前時間為白天，應該是充電期間）";

    var prompt =
      "請分析以下無線電中繼台的電源異常情況。該站台採用太陽能充電系統供電，市電供應不可用。" + timeCtx + "\n\n" +
      "設備: " + alert.device + "\n" +
      "異常類型: " + alert.type + "\n" +
      "目前電壓: " + alert.value + "\n" +
      "正常範圍: " + VOLTAGE_MIN + "V ~ " + VOLTAGE_MAX + "V\n" +
      "電壓趨勢: " + trend + "\n" +
      "變化速率: " + rate.toFixed(2) + "V/次\n\n" +
      "近期電壓紀錄（JSON）:\n" + JSON.stringify(history, null, 2) + "\n\n" +
      "請以繁體中文分析，回覆以下 JSON 格式（只回傳 JSON，不要 markdown）：\n" +
      "{\n" +
      "  \"risk\": \"高/中/低\",\n" +
      "  \"cause\": \"原因研判（20字內）\",\n" +
      "  \"diagnosis\": \"完整診斷說明（3-5句）\"\n" +
      "}";

    var payload = {
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { temperature: 0.3, maxOutputTokens: 512 }
    };

    var resp = UrlFetchApp.fetch(GEMINI_URL + GEMINI_KEY, {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });

    var respJson = JSON.parse(resp.getContentText());
    var raw = respJson.candidates[0].content.parts[0].text.trim();
    raw = raw.replace(/```json/g,"").replace(/```/g,"").trim();
    var aiResult = JSON.parse(raw);

    var timeLabel = isNight ? "晚間 " + hour + ":00" : "白天 " + hour + ":00";
    return JSON.stringify({
      ok:        true,
      risk:      aiResult.risk || "中",
      time:      alert.time + "\n" + timeLabel,
      volt:      alert.value + "（" + (parseFloat(alert.value) < VOLTAGE_MIN ? "低於" : "高於") + "正常）\n趨勢：" + trend + "\n速率：" + rate.toFixed(2) + "V/次",
      cause:     aiResult.cause || "原因不明",
      diagnosis: aiResult.diagnosis || "無分析結果"
    });

  } catch(e) {
    return JSON.stringify({ ok: false, error: e.toString() });
  }
}

function findCol(hdr, names) {
  for (var i = 0; i < hdr.length; i++) {
    var h = String(hdr[i]).toLowerCase();
    for (var j = 0; j < names.length; j++) {
      if (h.indexOf(names[j].toLowerCase()) >= 0) return i;
    }
  }
  return 1;
}
