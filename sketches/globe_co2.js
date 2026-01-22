let globe_co2 = function (p) {

    let table;
    let globeRadius = 220;
    let rotX = 0;
    let rotY = 0;
    let dragging = false;
    let lastX, lastY;
    let times = [];
    let minTime, maxTime;
    let timeSlider, playButton, playing = false;
    const CO2_MIN = 380;
    const CO2_MAX = 430;
    let hoveredPoint = null;
    let earthTexture, myFont;
    let zoom = 1;
    let cityInput, suggestionBox;
    let selectedAnchorCity = null;
    let allCities = [];
    let parent;

    p.preload = function () {
        table = p.loadTable("../data/CO2.csv", "csv", "header");
        earthTexture = p.loadImage("../data/earth.png");
        myFont = p.loadFont("../data/Roboto.ttf");
    }

    p.setup = function () {
        parent = document.getElementById("globe_co2");
        const canvas = p.createCanvas(1000, 900, p.WEBGL);
        canvas.parent(parent);
        p.textFont(myFont);

        for (let r = 0; r < table.getRowCount(); r++) times.push(new Date(table.getString(r, "datetime")).getTime());
        minTime = Math.min(...times);
        maxTime = Math.max(...times);

        timeSlider = p.createSlider(minTime, maxTime, minTime);
        timeSlider.parent(parent);
        timeSlider.position(20, 860);
        timeSlider.style("width", "600px");

        playButton = p.createButton("Play");
        playButton.parent(parent);
        playButton.position(640, 856);
        playButton.mousePressed(togglePlay);

        allCities = [...new Set(table.getColumn("city"))].filter(c => c);
        cityInput = p.createInput();
        cityInput.parent(parent);
        cityInput.size(150);
        cityInput.position(20, 610);
        cityInput.attribute('placeholder', 'Type a city...');
        cityInput.input(updateSuggestions);

        suggestionBox = p.createDiv();
        suggestionBox.parent(parent);
        suggestionBox.size(150);
        suggestionBox.style('background', '#222');
        suggestionBox.style('color', 'white');
        suggestionBox.style('padding', '5px');
        suggestionBox.style('max-height', '150px');
        suggestionBox.style('overflow-y', 'auto');
        suggestionBox.position(20, 630);
    }

    p.draw = function () {
        p.background(10);
        p.push();
        p.rotateX(rotX);
        p.rotateY(rotY);
        drawGraticule();
        drawGlobe();
        drawDataPoints();
        drawAnchorCityPin();
        p.pop();
        drawLegend();
        drawTimeLabel();
        drawAnchorCityCO2();
        drawTooltip();
        if (playing) advanceTime();
    }

    function drawGlobe() {
        p.ambientLight(120);
        p.directionalLight(255, 255, 255, 1, 1, -1);
        p.noStroke();
        p.fill(30);
        p.sphere(globeRadius * zoom, 48, 48);
    }

    function drawDataPoints() {
        hoveredPoint = null;
        let currentTime = timeSlider.value();
        let anchorCO2 = CO2_MIN;
        if (selectedAnchorCity) {
            for (let r = 0; r < table.getRowCount(); r++) {
                if (table.getString(r, "city") === selectedAnchorCity) {
                    let rowTime = new Date(table.getString(r, "datetime")).getTime();
                    if (rowTime <= currentTime) anchorCO2 = table.getNum(r, "xco2");
                }
            }
        }
        p.strokeWeight(5);
        for (let r = 0; r < table.getRowCount(); r++) {
            let rowTime = new Date(table.getString(r, "datetime")).getTime();
            if (rowTime > currentTime) continue;
            let lat = p.radians(table.getNum(r, "latitude"));
            let lon = p.radians(table.getNum(r, "longitude"));
            let xco2 = table.getNum(r, "xco2");
            let pos = latLonToXYZ(lat, lon, globeRadius * zoom);
            p.push();
            p.translate(pos.x, pos.y, pos.z);
            let normal = p.createVector(pos.x, pos.y, pos.z).normalize();
            let up = p.createVector(0, -1, 0);
            let axis = p5.Vector.cross(up, normal);
            let angle = Math.acos(p5.Vector.dot(up, normal));
            if (axis.mag() > 0) p.rotate(angle, axis);
            p.stroke(co2Color(xco2));
            p.point(0, 0, 0);
            p.pop();
            let mx = p.mouseX - p.width / 2;
            let my = p.mouseY - p.height / 2;
            let d = p.dist(mx, my, pos.x, pos.y);
            if (d < 8 && pos.z > 0) {
                hoveredPoint = { x: p.mouseX, y: p.mouseY, city: table.getString(r, "city"), country: table.getString(r, "country"), xco2: xco2, date: table.getString(r, "datetime") };
            }
        }
    }

    function drawAnchorCityPin() {
        if (!selectedAnchorCity) return;
        let currentTime = timeSlider.value();
        let lat, lon;
        for (let r = 0; r < table.getRowCount(); r++) {
            if (table.getString(r, "city") === selectedAnchorCity) {
                let rowTime = new Date(table.getString(r, "datetime")).getTime();
                if (rowTime <= currentTime) { lat = p.radians(table.getNum(r, "latitude")); lon = p.radians(table.getNum(r, "longitude")); }
            }
        }
        if (lat !== undefined && lon !== undefined) {
            let pos = latLonToXYZ(lat, lon, (globeRadius + 10) * zoom);
            p.push();
            p.translate(pos.x, pos.y, pos.z);
            let normal = p.createVector(pos.x, pos.y, pos.z).normalize();
            let up = p.createVector(0, -1, 0);
            let axis = p5.Vector.cross(up, normal);
            let angle = Math.acos(p5.Vector.dot(up, normal));
            p.rotate(angle, axis);
            p.fill(255, 0, 0);
            p.noStroke();
            p.cylinder(1.5 * zoom, 12 * zoom);
            p.sphere(3 * zoom);
            p.pop();
        }
    }

    function drawAnchorCityCO2() {
        if (!selectedAnchorCity) return;
        let currentTime = timeSlider.value();
        let co2 = null;
        for (let r = 0; r < table.getRowCount(); r++) {
            if (table.getString(r, "city") === selectedAnchorCity) {
                let rowTime = new Date(table.getString(r, "datetime")).getTime();
                if (rowTime <= currentTime) co2 = table.getNum(r, "xco2");
            }
        }
        if (co2 !== null) {
            p.push();
            p.fill(255);
            p.textFont(myFont);
            p.textSize(14);
            p.textAlign(p.LEFT);
            p.text(`${selectedAnchorCity} CO₂: ${co2.toFixed(1)} ppm`, -p.width / 2 + 20, p.height / 2 - 30);
            p.pop();
        }
    }

    function latLonToXYZ(lat, lon, r) {
        let x = r * Math.cos(lat) * Math.sin(lon);
        let y = -r * Math.sin(lat);
        let z = r * Math.cos(lat) * Math.cos(lon);
        return { x, y, z };
    }

    p.mousePressed = function () { dragging = true; lastX = p.mouseX; lastY = p.mouseY; }
    p.mouseReleased = function () { dragging = false; }
    p.mouseDragged = function () { if (p.mouseX < 0 || p.mouseX > p.width || p.mouseY < 0 || p.mouseY > p.height) return; if (!dragging) return; let dx = p.mouseX - lastX; let dy = p.mouseY - lastY; rotY += dx * 0.005; rotX += dy * 0.005; rotX = p.constrain(rotX, -Math.PI / 2, Math.PI / 2); lastX = p.mouseX; lastY = p.mouseY; }
    p.mouseWheel = function (event) { zoom -= event.delta * 0.001; zoom = p.constrain(zoom, 0.5, 2); }
    function togglePlay() { playing = !playing; playButton.html(playing ? "Pause" : "Play"); }
    function advanceTime() { let t = timeSlider.value(); t += (maxTime - minTime) / 600; if (t > maxTime) t = minTime; timeSlider.value(t); }
    function co2Color(value) { let t = p.constrain(p.map(value, CO2_MIN, CO2_MAX, 0, 1), 0, 1); let c1 = p.color(50, 150, 255); let c2 = p.color(100, 220, 120); let c3 = p.color(255, 220, 100); let c4 = p.color(220, 60, 60); if (t < 0.33) return p.lerpColor(c1, c2, t / 0.33); if (t < 0.66) return p.lerpColor(c2, c3, (t - 0.33) / 0.33); return p.lerpColor(c3, c4, (t - 0.66) / 0.34); }
    function drawLegend() { p.push(); p.translate(-p.width / 2 + 20, -p.height / 2 + 20); p.noStroke(); p.textFont(myFont); p.textSize(12); p.fill(220); p.text("XCO₂ (ppm)", 0, 0); for (let i = 0; i <= 100; i++) { p.fill(co2Color(p.map(i, 0, 100, CO2_MIN, CO2_MAX))); p.rect(i * 2, 10, 2, 10); } p.fill(180); p.textAlign(p.CENTER); p.text(CO2_MIN, 0, 35); p.text((CO2_MIN + CO2_MAX) / 2, 100, 35); p.text(CO2_MAX, 200, 35); p.pop(); }
    function drawTimeLabel() { let d = new Date(timeSlider.value()); let dateStr = d.toISOString().split("T")[0]; let timeStr = d.toTimeString().split(" ")[0]; p.push(); p.fill(255); p.noStroke(); p.textFont(myFont); p.textSize(14); p.textAlign(p.LEFT, p.CENTER); p.text(`Date: ${dateStr} ${timeStr}`, -p.width / 2 + 20, p.height / 2 - 60); p.pop(); }
    function drawTooltip() { if (!hoveredPoint) return; p.push(); p.fill(30, 220); p.noStroke(); p.textFont(myFont); p.textSize(11); p.textAlign(p.LEFT, p.TOP); p.rect(hoveredPoint.x + 10, hoveredPoint.y + 10, 180, 60, 6); p.fill(255); p.text(`${hoveredPoint.city}, ${hoveredPoint.country}\nXCO₂: ${hoveredPoint.xco2}\n${hoveredPoint.date}`, hoveredPoint.x + 16, hoveredPoint.y + 16); p.pop(); }
    function drawGraticule() { p.stroke(120, 120, 120, 80); p.noFill(); for (let lat = -75; lat <= 75; lat += 15) { p.beginShape(); for (let lon = -180; lon <= 180; lon += 5) { let pt = latLonToXYZ(p.radians(lat), p.radians(lon), (globeRadius + 1) * zoom); p.vertex(pt.x, pt.y, pt.z); } p.endShape(); } for (let lon = -180; lon < 180; lon += 15) { p.beginShape(); for (let lat = -90; lat <= 90; lat += 5) { let pt = latLonToXYZ(p.radians(lat), p.radians(lon), (globeRadius + 1) * zoom); p.vertex(pt.x, pt.y, pt.z); } p.endShape(); } }

    function updateSuggestions() {
        let val = cityInput.value().toLowerCase();
        suggestionBox.html('');
        if (val === '') return;
        let matches = allCities.filter(city => city.toLowerCase().startsWith(val));
        for (let city of matches) {
            let cityDiv = p.createDiv(city);
            cityDiv.parent(parent);
            cityDiv.style('padding', '3px');
            cityDiv.style('cursor', 'pointer');
            cityDiv.mousePressed(() => { selectedAnchorCity = city; cityInput.value(''); suggestionBox.html(''); });
        }
    }

};

new p5(globe_co2, 'globe_co2');
