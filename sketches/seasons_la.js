const seasons_la = (p) => {
    let table;
    let gapSlider;
    let gap = 4;
    let minLat, maxLat, minLon, maxLon;
    let minMercY, maxMercY;
    let minCO2 = Infinity;
    let maxCO2 = -Infinity;
    let panX = 0, panY = 0;
    let lastMouseX, lastMouseY;
    let dragging = false;
    const MAX_LAT = 85.05113;

    let showDJF = true, showMAM = true, showJJA = true, showSON = true;
    const seasonColors = {
        Winter: [0, 150, 255, 200],
        Spring: [0, 255, 0, 150],
        Summer: [255, 165, 0, 150],
        Fall: [255, 0, 0, 150]
    };
    let djfCheckbox, mamCheckbox, jjaCheckbox, sonCheckbox;
    let parent;

    p.preload = () => {
        table = p.loadTable(
            "../data/CO2_disaggregated_2019-2025_subset-USA-LA.csv",
            "csv",
            "header"
        );
    };

    p.setup = () => {
        parent = document.getElementById("seasons_la");
        parent.style.position = "relative";
        const c = p.createCanvas(parent.clientWidth, parent.clientWidth);
        c.parent(parent);
        c.style('position', 'absolute');
        c.style('top', '0px');
        c.style('left', '0px');
        c.style('z-index', '0');

        p.noStroke();
        minLat = 90; maxLat = -90; minLon = 180; maxLon = -180;

        for (let r = 0; r < table.getRowCount(); r++) {
            const lat = table.getNum(r, "latitude");
            const lon = table.getNum(r, "longitude");
            const co2 = table.getNum(r, "xco2");
            if (isNaN(lat) || isNaN(lon) || isNaN(co2)) continue;
            minLat = p.min(minLat, lat); maxLat = p.max(maxLat, lat);
            minLon = p.min(minLon, lon); maxLon = p.max(maxLon, lon);
            minCO2 = p.min(minCO2, co2); maxCO2 = p.max(maxCO2, co2);
        }

        minMercY = p.log(p.tan(p.PI / 4 + p.radians(minLat) / 2));
        maxMercY = p.log(p.tan(p.PI / 4 + p.radians(maxLat) / 2));

        gapSlider = p.createSlider(0.5, 20, gap, 0.1);
        gapSlider.parent(parent);
        gapSlider.position(10, parent.clientHeight - 40);
        gapSlider.style('position', 'absolute');
        gapSlider.style('z-index', '1');
        gapSlider.input(drawMap);

        djfCheckbox = p.createCheckbox("", showDJF);
        djfCheckbox.parent(parent);
        djfCheckbox.position(10, 10);
        djfCheckbox.style('position', 'absolute');
        djfCheckbox.style('z-index', '1');
        djfCheckbox.changed(() => { showDJF = djfCheckbox.checked(); drawMap(); });

        mamCheckbox = p.createCheckbox("", showMAM);
        mamCheckbox.parent(parent);
        mamCheckbox.position(10, 30);
        mamCheckbox.style('position', 'absolute');
        mamCheckbox.style('z-index', '1');
        mamCheckbox.changed(() => { showMAM = mamCheckbox.checked(); drawMap(); });

        jjaCheckbox = p.createCheckbox("", showJJA);
        jjaCheckbox.parent(parent);
        jjaCheckbox.position(10, 50);
        jjaCheckbox.style('position', 'absolute');
        jjaCheckbox.style('z-index', '1');
        jjaCheckbox.changed(() => { showJJA = jjaCheckbox.checked(); drawMap(); });

        sonCheckbox = p.createCheckbox("", showSON);
        sonCheckbox.parent(parent);
        sonCheckbox.position(10, 70);
        sonCheckbox.style('position', 'absolute');
        sonCheckbox.style('z-index', '1');
        sonCheckbox.changed(() => { showSON = sonCheckbox.checked(); drawMap(); });

        drawMap();
    };

    function drawMap() {
        p.background(0);
        gap = gapSlider.value();
        p.push();
        p.translate(p.width / 2 + panX, p.height / 2 + panY);
        p.scale(gap);
        p.translate(-p.width / 2, -p.height / 2);

        for (let r = 0; r < table.getRowCount(); r++) {
            let lat = table.getNum(r, "latitude");
            let lon = table.getNum(r, "longitude");
            let co2 = table.getNum(r, "xco2");
            let datetimeStr = table.getString(r, "datetime");
            if (isNaN(lat) || isNaN(lon) || isNaN(co2) || !datetimeStr) continue;

            const date = new Date(datetimeStr.replace(/\s+/g, " "));
            if (isNaN(date)) continue;
            const month = date.getMonth();
            let season = month === 11 || month <= 1 ? "Winter" :
                month <= 4 ? "Spring" :
                    month <= 7 ? "Summer" : "Fall";

            if ((season === "Winter" && !showDJF) ||
                (season === "Spring" && !showMAM) ||
                (season === "Summer" && !showJJA) ||
                (season === "Fall" && !showSON)) continue;

            p.fill(seasonColors[season]);
            lat = p.constrain(lat, -MAX_LAT, MAX_LAT);
            const x = p.map(lon, minLon, maxLon, 0, p.width);
            const mercY = p.log(p.tan(p.PI / 4 + p.radians(lat) / 2));
            const y = p.map(mercY, minMercY, maxMercY, p.height, 0);
            const d = p.map(co2, minCO2, maxCO2, 2, 10);
            p.circle(x, y, d / gap);
        }

        p.pop();
        drawLegend();
    }

    function drawLegend() {
        p.push();
        const legendX = p.width - 280;
        const legendY = 0;
        p.fill(255);
        p.textSize(12);
        // p.text("Season Colors:", legendX, legendY);
        ["Winter", "Spring", "Summer", "Fall"].forEach((s, i) => {
            p.fill(seasonColors[s]);
            p.rect(legendX, legendY + 15 + i * 20, 12, 12);
            p.fill(255);
            p.text(s, legendX + 20, legendY + 27 + i * 20);
        });
        p.pop();
    }

    p.mousePressed = () => {
        dragging = true;
        lastMouseX = p.mouseX; lastMouseY = p.mouseY;
    };
    p.mouseDragged = () => {
        if (!dragging) return;
        panX += p.mouseX - lastMouseX;
        panY += p.mouseY - lastMouseY;
        lastMouseX = p.mouseX; lastMouseY = p.mouseY;
        drawMap();
    };
    p.mouseReleased = () => { dragging = false; };
};

new p5(seasons_la, 'seasons_la');
