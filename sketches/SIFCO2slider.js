let SIFCO2slider = function(p) {

  let co2Table, sifTable;
  let yearlyData = {};        
  let years = ["2019","2020","2021","2022","2023","2024","2025"]; 
  let selectedYear = "2019";

  //colors
  let minCO2 = 380; //fixed for ppm
  let maxCO2 = 430;
  let minSIF = Infinity;
  let maxSIF = -Infinity;

  //vertical slider to separate CO2 vs SIF
  let layerSliderY;
  let draggingSlider = false;

  //time slider
  let timeSlider;

  //map boundaries
  let mapX1 = 50;
  let mapX2 = 600;
  let mapY1 = 50;
  let mapY2 = 700;

  //legend position
  let legendX = 650;
  let legendY = 100;
  let legendHeight = 200;
  let legendWidth = 20;

  p.preload = function() {
    co2Table = p.loadTable("../data/CO2_combined.csv", "csv", "header");
    sifTable = p.loadTable("../data/SIF_combined.csv", "csv", "header");
  }

  p.setup = function() {
    p.createCanvas(1000, 800);
    p.colorMode(p.HSB);
    p.noStroke();

    layerSliderY = (mapY1 + mapY2) / 2;

    //process CO2 data
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
      if (!yearlyData[year][key]) yearlyData[year][key] = {lat, lon, country};
      yearlyData[year][key].co2 = co2;
    }

    //process SIF data
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
      if (!yearlyData[year][key]) yearlyData[year][key] = {lat, lon, country};
      yearlyData[year][key].sif = sif;

      minSIF = p.min(minSIF, sif);
      maxSIF = p.max(maxSIF, sif);
    }

    //time slider
    timeSlider = p.createSlider(0, years.length - 1, 0, 1);
    timeSlider.position(mapX1, 20);
    timeSlider.style('width', mapX2 - mapX1 + 'px');
    timeSlider.input(() => selectedYear = years[timeSlider.value()]);
  }

  p.draw = function() {
    p.background(0);

    //draw the world map data for selectedYear
    drawYear(selectedYear);

    //draw vertical layer slider
    p.stroke(255);
    p.strokeWeight(2);
    p.line(mapX1, layerSliderY, mapX2, layerSliderY);
    p.fill(255);
    p.noStroke();
    p.textSize(16);
    p.textAlign(p.LEFT, p.BOTTOM);
    p.text("SIF above, CO2 below", mapX2 + 10, layerSliderY);

    //draw selected year
    p.fill(255);
    p.textSize(20);
    p.textAlign(p.LEFT, p.TOP);
    p.text("Year: " + selectedYear, mapX1, 50);

    //legends
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
        let radius = p.map(d.sif, minSIF, maxSIF, 3, 15);
        let c = p.color(p.map(d.sif, minSIF, maxSIF, 180,360), 80, 100);
        p.fill(c);
        p.noStroke();
        p.ellipse(x, y, radius*2);
      } else if (y >= layerSliderY && d.co2 !== undefined) {
        let radius = p.map(d.co2, minCO2, maxCO2, 3, 15);
        let c = p.color(p.map(d.co2, minCO2, maxCO2, 120, 0), 80, 100);
        p.fill(c);
        p.noStroke();
        p.ellipse(x, y, radius*2);
      } else {
        p.fill(0, 0, 30);
        p.noStroke();
        p.ellipse(x, y, 10);
      }
    }
  }

  //vertical slider drag
  p.mousePressed = function() {
    if (p.mouseY > layerSliderY - 10 && p.mouseY < layerSliderY + 10) {
      draggingSlider = true;
    }
  }

  p.mouseReleased = function() {
    draggingSlider = false;
  }

  p.mouseDragged = function() {
    if (draggingSlider) {
      layerSliderY = p.constrain(p.mouseY, mapY1, mapY2);
    }
  }

  function drawLegend() {
    p.textSize(12);
    p.textAlign(p.LEFT, p.CENTER);

    for (let i = 0; i <= legendHeight; i++) {
      let inter = p.map(i, 0, legendHeight, minCO2, maxCO2);
      let c = p.color(p.map(inter, minCO2, maxCO2, 0, 180), 80, 100);
      p.stroke(c);
      p.line(legendX, legendY + i, legendX + legendWidth, legendY + i);
    }
    p.noStroke();
    p.fill(255);
    p.text("CO2 ppm", legendX + 30, legendY + legendHeight/2);
    p.text(minCO2, legendX, legendY + legendHeight);
    p.text(maxCO2, legendX, legendY);

    // SIF legend
    for (let i = 0; i <= legendHeight; i++) {
      let inter = p.map(i, 0, legendHeight, maxSIF, minSIF);
      let c = p.color(p.map(inter, minSIF, maxSIF, 180,360), 80, 100);
      p.stroke(c);
      p.line(legendX + 60, legendY + i, legendX + 60 + legendWidth, legendY + i);
    }
    p.noStroke();
    p.fill(255);
    p.text("SIF", legendX + 90, legendY + legendHeight/2);
    p.text(minSIF.toFixed(2), legendX + 60, legendY + legendHeight);
    p.text(maxSIF.toFixed(2), legendX + 60, legendY);
  }

};

new p5(SIFCO2slider, 'SIFCO2slider'); 
