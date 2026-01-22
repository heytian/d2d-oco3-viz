let SIFCO2slider = function (p) {

  let co2Table, sifTable;
  let yearlyData = {};
  let years = ["2019", "2020", "2021", "2022", "2023", "2024", "2025"];
  let selectedYear = "2019";

  let minCO2 = 380;
  let maxCO2 = 430;
  let minSIF = Infinity;
  let maxSIF = -Infinity;

  let layerSliderY;
  let draggingSlider = false;

  let timeSlider;
  let parent;

  let mapX1, mapX2, mapY1, mapY2;
  let legendX, legendY, legendHeight, legendWidth;

  p.preload = function () {
    co2Table = p.loadTable("../data/CO2_combined.csv", "csv", "header");
    sifTable = p.loadTable("../data/SIF_combined.csv", "csv", "header");
  }

  p.setup = function () {
    parent = document.getElementById("SIFCO2slider");
    let canvas = p.createCanvas(650, 400); // adjust canvas dimensions as desired
    canvas.parent(parent);
    p.colorMode(p.HSB);
    p.textFont('Helvetica');

    mapX1 = p.width * 0.07;
    mapX2 = p.width * 0.7;
    mapY1 = p.height * 0.07;
    mapY2 = p.height * 0.85;

    legendX = p.width * 0.78;
    legendY = p.height * 0.07;
    legendHeight = p.height * 0.25;
    legendWidth = p.width * 0.02;

    layerSliderY = (mapY1 + mapY2) / 2;

    for (let i = 0; i < co2Table.getRowCount(); i++) {
      let r = co2Table.getRow(i);
      let rawTime = r.getString("datetime");
      if (!rawTime) continue;
      let dateParts = rawTime.split(" ")[0].split("/");
      if (dateParts.length !== 3) continue;
      let year = "20" + dateParts[2];
      if (!years.includes(year)) continue;
      let lat = parseFloat(r.getString("latitude"));
      let lon = parseFloat(r.getString("longitude"));
      let co2 = parseFloat(r.getString("xco2"));
      let country = r.getString("country");
      if (isNaN(lat) || isNaN(lon) || isNaN(co2)) continue;
      if (!yearlyData[year]) yearlyData[year] = {};
      let key = lat + "_" + lon;
      if (!yearlyData[year][key]) yearlyData[year][key] = { lat, lon, country };
      yearlyData[year][key].co2 = co2;
    }

    for (let i = 0; i < sifTable.getRowCount(); i++) {
      let r = sifTable.getRow(i);
      let rawTime = r.getString("datetime");
      if (!rawTime) continue;
      let dateParts = rawTime.split(" ")[0].split("/");
      if (dateParts.length !== 3) continue;
      let year = "20" + dateParts[2];
      if (!years.includes(year)) continue;
      let lat = parseFloat(r.getString("latitude"));
      let lon = parseFloat(r.getString("longitude"));
      let sif = parseFloat(r.getString("Daily_SIF_757nm"));
      let country = r.getString("country");
      if (isNaN(lat) || isNaN(lon) || isNaN(sif)) continue;
      if (!yearlyData[year]) yearlyData[year] = {};
      let key = lat + "_" + lon;
      if (!yearlyData[year][key]) yearlyData[year][key] = { lat, lon, country };
      yearlyData[year][key].sif = sif;
      minSIF = p.min(minSIF, sif);
      maxSIF = p.max(maxSIF, sif);
    }

    timeSlider = p.createSlider(0, years.length - 1, 0, 1);
    timeSlider.parent(parent);
    timeSlider.input(() => selectedYear = years[timeSlider.value()]);
  }

  p.draw = function () {
    p.background(0);

    mapX1 = p.width * 0.07;
    mapX2 = p.width * 0.7;
    mapY1 = p.height * 0.07;
    mapY2 = p.height * 0.85;

    legendX = p.width * 0.78;
    legendY = p.height * 0.07;
    legendHeight = p.height * 0.25;
    legendWidth = p.width * 0.02;

    layerSliderY = p.constrain(layerSliderY, mapY1, mapY2);

    timeSlider.position(mapX1, mapY2 + p.height * 0.03);
    timeSlider.style('width', (mapX2 - mapX1) + 'px');

    drawYear(selectedYear);

    p.stroke(255);
    p.strokeWeight(p.width * 0.003);
    p.line(mapX1, layerSliderY, mapX2, layerSliderY);

    p.fill(255);
    p.noStroke();
    p.textSize(p.width * 0.02);
    p.textAlign(p.LEFT, p.BOTTOM);
    p.text("SIF above, CO2 below", mapX2 + p.width * 0.015, layerSliderY);

    p.fill(255);
    p.textSize(p.width * 0.03);
    p.textAlign(p.LEFT, p.TOP);
    p.text("Year: " + selectedYear, mapX1, mapY1 - p.height * 0.03);

    drawLegend();
  }

  function drawYear(year) {
    let data = yearlyData[year];
    if (!data) return;
    for (let key in data) {
      let d = data[key];
      let x = p.map(d.lon, -180, 180, mapX1, mapX2);
      let y = p.map(d.lat, 90, -90, mapY1, mapY2);
      if (y < layerSliderY && d.sif !== undefined) {
        let radius = p.map(d.sif, minSIF, maxSIF, 3, 12);
        let c = p.color(p.map(d.sif, minSIF, maxSIF, 180, 360), 80, 100);
        p.fill(c);
        p.noStroke();
        p.ellipse(x, y, radius * 2);
      } else if (y >= layerSliderY && d.co2 !== undefined) {
        let radius = p.map(d.co2, minCO2, maxCO2, 3, 12);
        let c = p.color(p.map(d.co2, minCO2, maxCO2, 120, 0), 80, 100);
        p.fill(c);
        p.noStroke();
        p.ellipse(x, y, radius * 2);
      } else {
        p.fill(0, 0, 30);
        p.noStroke();
        p.ellipse(x, y, 8);
      }
    }
  }

  p.mousePressed = function () {
    if (p.mouseY > layerSliderY - 8 && p.mouseY < layerSliderY + 8) draggingSlider = true;
  }
  p.mouseReleased = function () { draggingSlider = false; }
  p.mouseDragged = function () { if (draggingSlider) layerSliderY = p.constrain(p.mouseY, mapY1, mapY2); }

  p.drawLegend = function () {
    p.push();
    const legendX = p.width - 100;
    const legendY = 20;
    p.textSize(12);
    p.fill(0);
    p.text("Season Colors:", legendX, legendY);

    ["Winter", "Spring", "Summer", "Fall"].forEach((s, i) => {
      p.fill(seasonColors[s]);
      p.rect(legendX, legendY + 15 + i * 20, 12, 12);
      p.fill(0);
      p.text(s, legendX + 20, legendY + 27 + i * 20);
    });
    p.pop();
  }

};

new p5(SIFCO2slider, 'SIFCO2slider');
