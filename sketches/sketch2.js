function setup() {
  createCanvas(300, 300);
}

function draw() {
  background(220);
}

// begin sketch from p5js code

let table;
let yearlyData = {};        
let years = ["2019","2020","2021","2022","2023","2024","2025"]; 
let selectedYear = "2019";
let countryColors = {};    
let minCO2 = Infinity;
let maxCO2 = -Infinity;

//timeline positions
let timelineY = 750;
let timelineX1 = 50; //adjusted for main map width
let timelineX2 = 600;
let timelineDots = [];

//city selection w/autocompletion
let cityInput;
let suggestionBox;
let selectedCities = [];
let allCities = [];

//smaller map
let miniMapY = 400; 
let slider; 
let selectedDate = ""; 
let dailyData = {};

//side panel
let sidePanelX = 650;

function preload() {
  table = loadTable("combined.csv", "csv", "header");
}

function setup() {
  createCanvas(1000, 800);
  colorMode(HSB);
  noStroke();

  //data grouped by year
  for (let i = 0; i < table.getRowCount(); i++) {
    let rdata = table.getRow(i);
    let rawTime = rdata.getString("datetime");
    if (!rawTime) continue;

    // Parse MM/DD/YY
    let dateParts = rawTime.split(" ")[0].split("/");
    if (dateParts.length !== 3) continue;
    let year = "20" + dateParts[2];
    if (!years.includes(year)) continue;

    let lat = parseFloat(rdata.getString("latitude"));
    let lon = parseFloat(rdata.getString("longitude"));
    let co2 = parseFloat(rdata.getString("xco2"));
    let country = rdata.getString("country");
    let city = rdata.getString("city");

    if (isNaN(lat) || isNaN(lon) || isNaN(co2)) continue;

    if (!yearlyData[year]) yearlyData[year] = [];
    yearlyData[year].push({ lat, lon, co2, country, city });

    minCO2 = min(minCO2, co2);
    maxCO2 = max(maxCO2, co2);

    //daily data
    if (!dailyData[city]) dailyData[city] = [];
    dailyData[city].push({ datetime: new Date(rawTime), lat, lon, co2, country });
  }

  //sort daily stamps per city
  for (let city in dailyData) {
    dailyData[city].sort((a,b) => a.datetime - b.datetime);
  }

  // Assign colors to countries
  let countries = [...new Set(table.getColumn("country"))].filter(c => c);
  for (let i = 0; i < countries.length; i++) {
    let hue = map(i, 0, countries.length, 0, 360);
    countryColors[countries[i]] = color(hue, 70, 100);
  }

  // Calculate timeline dot positions
  for (let i = 0; i < years.length; i++) {
    let x = map(i, 0, years.length - 1, timelineX1, timelineX2);
    timelineDots.push({ x, year: years[i] });
  }

  // Prepare city input and suggestions
  allCities = [...new Set(table.getColumn("city"))].filter(c => c);

  cityInput = createInput();
  cityInput.position(sidePanelX + 20, 60);
  cityInput.size(200);
  cityInput.attribute('placeholder', 'Type a city...');
  cityInput.input(updateSuggestions);

  suggestionBox = createDiv();
  suggestionBox.position(sidePanelX + 20, 85);
  suggestionBox.size(200);
  suggestionBox.style('background', '#222');
  suggestionBox.style('color', 'white');
  suggestionBox.style('padding', '5px');
  suggestionBox.style('max-height', '150px');
  suggestionBox.style('overflow-y', 'auto');

  // Mini-map slider
  let minDate = new Date("2019-01-01");
  let maxDate = new Date("2025-12-31");
  slider = createSlider(minDate.getTime(), maxDate.getTime(), minDate.getTime());
  slider.position(sidePanelX + 20, miniMapY + 200);
  slider.style('width', '200px');
  slider.input(() => {
    selectedDate = new Date(slider.value());
  });
  selectedDate = new Date(slider.value());
}

function draw() {
  background(0);

  //co2 data for selected year
  drawYear(selectedYear);

  //timeline
  stroke(255);
  strokeWeight(2);
  line(timelineX1, timelineY, timelineX2, timelineY);

  noStroke();
  for (let d of timelineDots) {
    if (d.year === selectedYear) fill(0, 0, 100);
    else fill(200, 70, 100);
    ellipse(d.x, timelineY, 20);
    fill(255);
    textSize(16);
    textAlign(CENTER, BOTTOM);
    text(d.year, d.x, timelineY - 10);
  }

  //selected year
  fill(255);
  textSize(22);
  textAlign(LEFT);
  text(selectedYear, 20, 40);

  drawSelectedCities();

  drawMiniMap();
}

function drawYear(year) {
  let rows = yearlyData[year];
  if (!rows || rows.length === 0) return;

  for (let d of rows) {
    let x = map(d.lon, -180, 180, 50, 600); // adjusted to main map width
    let y = map(d.lat, 90, -90, 50, 700);

    let radius = map(d.co2, minCO2, maxCO2, 5, 35);

    let c = countryColors[d.country] || color(0, 0, 100);

    if (selectedCities.includes(d.city)) {
      stroke(0, 0, 100);
      strokeWeight(3);
    } else {
      noStroke();
    }

    fill(c);
    ellipse(x, y, radius * 2);
  }
}

function mousePressed() {
  for (let d of timelineDots) {
    if (dist(mouseX, mouseY, d.x, timelineY) < 15) {
      selectedYear = d.year;
      break;
    }
  }
}

function updateSuggestions() {
  let val = cityInput.value().toLowerCase();
  suggestionBox.html('');

  if (val === '') return;

  let matches = allCities.filter(city => city.toLowerCase().startsWith(val));
  for (let city of matches) {
    let cityDiv = createDiv(city);
    cityDiv.parent(suggestionBox);
    cityDiv.style('padding', '3px');
    cityDiv.style('cursor', 'pointer');
    cityDiv.mousePressed(() => {
      if (!selectedCities.includes(city)) selectedCities.push(city);
      cityInput.value('');
      suggestionBox.html('');
    });
  }
}

function drawSelectedCities() {
  fill(255);
  textSize(16);
  textAlign(LEFT);
  text("Selected Cities:", sidePanelX + 20, 250);

  for (let i = 0; i < selectedCities.length; i++) {
    text(selectedCities[i], sidePanelX + 20, 270 + i * 20);
  }
}

function drawMiniMap() {
  fill(50);
  rect(sidePanelX, miniMapY, 250, 250);

  if (selectedCities.length === 0) return;

  for (let city of selectedCities) {
    let cityData = dailyData[city];
    if (!cityData) continue;

    let nearest = null;
    for (let d of cityData) {
      if (d.datetime <= selectedDate) nearest = d;
      else break;
    }
    if (!nearest) continue;

    let x = map(nearest.lon, -180, 180, sidePanelX + 10, sidePanelX + 240);
    let y = map(nearest.lat, 90, -90, miniMapY + 10, miniMapY + 240);
    let radius = map(nearest.co2, minCO2, maxCO2, 5, 20);
    let c = countryColors[nearest.country] || color(0, 0, 100);

    fill(c);
    noStroke();
    ellipse(x, y, radius*2);
  }

  fill(255);
  textSize(12);
  textAlign(LEFT);
  text(selectedDate.toDateString(), sidePanelX + 20, miniMapY + 230);
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










