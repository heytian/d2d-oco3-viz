function setup() {
  createCanvas(300, 300);
}

function draw() {
  background(220);
}

// begin sketch from p5js code

let cities = [];

let topColor;
let bottomColor;

let months = [];
let monthKeys = [];
let currentMonthIndex = 0;

let co2Table;
let co2Series = {};
let sifSeries = {};

let co2Min = Infinity;
let co2Max = -Infinity;
let sifMin = 0;
let sifMax = 1.5;

let barInfo = [];

function preload() {
  co2Table = loadTable("combined.csv", "csv", "header");
}

function setup() {
  createCanvas(1400, 700);
  textAlign(CENTER, CENTER);

  topColor = color(255, 80, 80);
  bottomColor = color(160, 0, 0);

  let cityMonthCo2 = {};
  let monthSet = new Set();

  for (let r = 0; r < co2Table.getRowCount(); r++) {
    let rawCity = co2Table.getString(r, "city");
    if (!cities.includes(rawCity)) cities.push(rawCity);
  }

  for (let r = 0; r < co2Table.getRowCount(); r++) {
    let city = co2Table.getString(r, "city");
    let v = co2Table.getNum(r, "xco2");
    if (!isFinite(v)) continue;

    let datetime = co2Table.getString(r, "datetime");
    let datePart = datetime.split(" ")[0];
    let parts = datePart.split("/");
    let m = int(parts[0]);
    let yy = int(parts[2]);
    let y = 2000 + yy;
    let key = y + "-" + nf(m, 2);

    monthSet.add(key);

    if (!cityMonthCo2[city]) cityMonthCo2[city] = {};
    if (!cityMonthCo2[city][key]) cityMonthCo2[city][key] = {sum:0, count:0};
    cityMonthCo2[city][key].sum += v;
    cityMonthCo2[city][key].count += 1;
  }

  monthKeys = Array.from(monthSet).sort();
  for (let k of monthKeys) {
    let parts = k.split("-");
    let y = int(parts[0]);
    let m = int(parts[1]);
    months.push(`${monthName(m)} ${y}`);
  }

  for (let city of cities) {
    let raw = cityMonthCo2[city];
    if (!raw) continue;

    let arr = [];
    let lastVal = null;

    for (let i = 0; i < monthKeys.length; i++) {
      let key = monthKeys[i];
      let entry = raw[key];
      let value = null;
      if (entry) {
        value = entry.sum / entry.count;
        lastVal = value;
      } else if (lastVal !== null) {
        value = lastVal;
      }
      arr[i] = value;
    }

    let firstIdx = -1;
    for (let i = 0; i < arr.length; i++) {
      if (arr[i] != null) {
        firstIdx = i;
        break;
      }
    }
    if (firstIdx === -1) continue;

    let current = arr[firstIdx];
    for (let i = 0; i < firstIdx; i++) arr[i] = current;
    for (let i = firstIdx; i < arr.length; i++) {
      if (arr[i] == null) arr[i] = current;
      else current = arr[i];
    }

    co2Series[city] = arr;

    for (let v of arr) {
      if (!isFinite(v)) continue;
      if (v < co2Min) co2Min = v;
      if (v > co2Max) co2Max = v;
    }
  }

  if (!isFinite(co2Min) || !isFinite(co2Max) || co2Max === co2Min) {
    co2Min = 400;
    co2Max = 430;
  }

  for (let city in co2Series) {
    let arr = co2Series[city];
    let sArr = [];
    for (let v of arr) {
      let norm = (v - co2Min) / (co2Max - co2Min);
      norm = constrain(norm, 0, 1);
      sArr.push(sifMax * (1 - norm));
    }
    sifSeries[city] = sArr;
  }
}

function draw() {
  background(245);

  if (months.length === 0) {
    fill(0);
    textSize(24);
    text("No data loaded", width/2, height/2);
    return;
  }

  let t = millis() / 100;
  currentMonthIndex = floor(t) % months.length;

  fill(0);
  textAlign(LEFT, TOP);
  textSize(28);
  text(months[currentMonthIndex], 60, 15);

  let centerY = height * 0.45;
  let maxUp = 120;
  let maxDown = 100;

  let leftMargin = 80;
  let rightMargin = 40;
  let usableWidth = width - leftMargin - rightMargin;

  let spacing = usableWidth / max(cities.length, 1);
  let barWidth = min(spacing * 0.7, 14);

  drawCO2Scale(centerY, maxUp);
  drawSIFScale(centerY, maxDown);

  barInfo = [];

  for (let i = 0; i < cities.length; i++) {
    let city = cities[i];
    let co2Arr = co2Series[city];
    let sifArr = sifSeries[city];
    if (!co2Arr && !sifArr) continue;

    let x = leftMargin + spacing * i + spacing * 0.5;

    let co2Val = co2Arr ? co2Arr[currentMonthIndex] : null;
    let upH = 0;
    if (co2Val != null) {
      upH = map(co2Val, co2Min, co2Max, 5, maxUp);
      fill(topColor);
      rectMode(CORNER);
      rect(x - barWidth/2, centerY - upH, barWidth, upH);
    }

    let sifVal = sifArr ? sifArr[currentMonthIndex] : null;
    let downH = 0;
    if (sifVal != null) {
      downH = map(sifVal, sifMin, sifMax, 5, maxDown);
      fill(bottomColor);
      rectMode(CORNER);
      rect(x - barWidth/2, centerY, barWidth, downH);
    }

    barInfo.push({
      city,
      x,
      barWidth,
      centerY,
      upH,
      downH,
      co2Val,
      sifVal
    });
  }

  stroke(0);
  line(0, centerY, width, centerY);

  noStroke();
  fill(0);
  textAlign(LEFT, CENTER);
  textSize(18);
  text("CO₂ (ppm)", 60, centerY - maxUp - 40);
  text("SIF", 60, centerY + maxDown + 40);

  drawTooltip();
}

function drawTooltip() {
  let hovered = null;

  for (let info of barInfo) {
    let x1 = info.x - info.barWidth/2;
    let x2 = info.x + info.barWidth/2;
    let yTop = info.centerY - info.upH;
    let yBottom = info.centerY + info.downH;

    if (mouseX >= x1 && mouseX <= x2 && mouseY >= yTop && mouseY <= yBottom) {
      hovered = info;
      break;
    }
  }

  if (!hovered) return;

  let tipText1 = hovered.city;
  let tipText2 = hovered.co2Val != null ? `CO₂: ${nf(hovered.co2Val,1,1)} ppm` : "";
  let tipText3 = hovered.sifVal != null ? `SIF: ${nf(hovered.sifVal,1,3)}` : "";

  textSize(14);
  let w1 = textWidth(tipText1);
  let w2 = textWidth(tipText2);
  let w3 = textWidth(tipText3);
  let tw = max(w1, w2, w3) + 20;
  let th = 50;

  let tx = hovered.x;
  let ty = hovered.centerY - hovered.upH - 25;
  if (ty - th < 0) ty = hovered.centerY + hovered.downH + 25;
  if (tx - tw/2 < 0) tx = tw/2 + 5;
  if (tx + tw/2 > width) tx = width - tw/2 - 5;

  rectMode(CENTER);
  fill(255);
  stroke(0);
  rect(tx, ty, tw, th, 6);

  noStroke();
  fill(0);
  textAlign(CENTER, CENTER);
  let lineY = ty - 12;
  text(tipText1, tx, lineY);
  lineY += 14;
  if (tipText2 !== "") text(tipText2, tx, lineY);
  lineY += 14;
  if (tipText3 !== "") text(tipText3, tx, lineY);
}

function drawCO2Scale(centerY, maxUp) {
  let axisX = 40;
  stroke(0);
  strokeWeight(1.2);
  line(axisX, centerY, axisX, centerY - maxUp);

  let ticks = 5;
  textAlign(RIGHT, CENTER);
  textSize(14);
  fill(0);

  for (let i = 1; i <= ticks; i++) {      // start at 1 so no label at center
    let y = centerY - (i / ticks) * maxUp;
    let value = lerp(co2Min, co2Max, i / ticks);
    let label = nf(value, 1, 1);
    noStroke();
    text(label, axisX - 8, y);
    stroke(0);
    line(axisX - 4, y, axisX, y);
  }
}

function drawSIFScale(centerY, maxDown) {
  let axisX = 40;
  stroke(0);
  strokeWeight(1.2);
  line(axisX, centerY, axisX, centerY + maxDown);

  let ticks = 5;
  textAlign(RIGHT, CENTER);
  textSize(14);
  fill(0);

  for (let i = 0; i <= ticks; i++) {
    let y = centerY + (i / ticks) * maxDown;
    let value = lerp(sifMin, sifMax, i / ticks);
    let label = nf(value, 1, 2);
    noStroke();
    text(label, axisX - 8, y);
    stroke(0);
    line(axisX - 4, y, axisX, y);
  }
}

function monthName(m) {
  return ["Jan","Feb","Mar","Apr","May","Jun","Jul",
          "Aug","Sep","Oct","Nov","Dec"][m-1];
}

// After

export default function sketch(p, size = 300) {

  p.setup = () => {
    p.createCanvas(size, size);
  };

  p.draw = () => {
    p.background(220);
  };

}

