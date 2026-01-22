const seasons_sif = (p) => {
    let table;
    let gapSlider;
    let gap = 4;
    let minLat = -85.05113, maxLat = 85.05113;
    let minLon = -180, maxLon = 180;
    let minMercY, maxMercY;
    let minSIF = Infinity, maxSIF = -Infinity;
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


    let times = [];
    let currentTimeIndex = 0;
    let cumulativePoints = [];
    let playing = true;


    let speedSlider;


    let hoverData = null;

    p.preload = () => {
        table = p.loadTable(
            "../data/SIF_disagg_geocode_2019-2025.csv",
            "csv",
            "header"
        );
    };

    p.setup = () => {
        parent = document.getElementById("seasons_sif");
        parent.style.position = "relative";
        const c = p.createCanvas(parent.clientWidth, parent.clientWidth);
        c.parent(parent);
        c.style('position', 'absolute');
        c.style('top', '0px');
        c.style('left', '0px');
        c.style('z-index', '0');

        p.noStroke();
        minMercY = p.log(p.tan(p.PI / 4 + p.radians(minLat) / 2));
        maxMercY = p.log(p.tan(p.PI / 4 + p.radians(maxLat) / 2));

        const timeSet = new Set();
        for (let r = 0; r < table.getRowCount(); r++) {
            const s = table.getNum(r, "Daily_SIF_");
            if (!isNaN(s)) minSIF = p.min(minSIF, s);
            const dt = table.getString(r, "datetime");
            if (dt) timeSet.add(dt);
        }
        times = Array.from(timeSet).sort((a, b) => new Date(a) - new Date(b));

        gapSlider = p.createSlider(0.5, 20, gap, 0.1);
        gapSlider.parent(parent);
        gapSlider.position(10, parent.clientHeight - 40);
        gapSlider.style('position', 'absolute');
        gapSlider.style('z-index', '1');
        gapSlider.input(() => gap = gapSlider.value());

        speedSlider = p.createSlider(1, 50, 5, 1);
        speedSlider.parent(parent);
        speedSlider.position(150, parent.clientHeight - 40);
        speedSlider.style('position', 'absolute');
        speedSlider.style('z-index', '1');

        // season checkboxes
        djfCheckbox = p.createCheckbox("", showDJF);
        djfCheckbox.parent(parent);
        djfCheckbox.position(10, 10);
        djfCheckbox.changed(() => { showDJF = djfCheckbox.checked(); });

        mamCheckbox = p.createCheckbox("", showMAM);
        mamCheckbox.parent(parent);
        mamCheckbox.position(10, 30);
        mamCheckbox.changed(() => { showMAM = mamCheckbox.checked(); });

        jjaCheckbox = p.createCheckbox("", showJJA);
        jjaCheckbox.parent(parent);
        jjaCheckbox.position(10, 50);
        jjaCheckbox.changed(() => { showJJA = jjaCheckbox.checked(); });

        sonCheckbox = p.createCheckbox("", showSON);
        sonCheckbox.parent(parent);
        sonCheckbox.position(10, 70);
        sonCheckbox.changed(() => { showSON = sonCheckbox.checked(); });
    };

    p.draw = () => {
        if (playing && currentTimeIndex < times.length) {
            const currentTimeStr = times[currentTimeIndex];
            const speed = speedSlider.value();

            for (let step = 0; step < speed; step++) {
                if (currentTimeIndex >= times.length) break;
                const timeStr = times[currentTimeIndex];
                for (let r = 0; r < table.getRowCount(); r++) {
                    const lat = table.getNum(r, "latitude");
                    const lon = table.getNum(r, "longitude");
                    const sif = table.getNum(r, "Daily_SIF_");
                    const datetimeStr = table.getString(r, "datetime");
                    const city = table.getString(r, "city");
                    const country = table.getString(r, "country");
                    if (isNaN(lat) || isNaN(lon) || isNaN(sif) || !datetimeStr) continue;
                    if (datetimeStr !== timeStr) continue;

                    const date = new Date(datetimeStr.replace(/\s+/g, " "));
                    const month = date.getMonth();
                    let season = month === 11 || month <= 1 ? "Winter" :
                        month <= 4 ? "Spring" :
                            month <= 7 ? "Summer" : "Fall";

                    if ((season === "Winter" && !showDJF) ||
                        (season === "Spring" && !showMAM) ||
                        (season === "Summer" && !showJJA) ||
                        (season === "Fall" && !showSON)) continue;

                    cumulativePoints.push({ lat, lon, sif, season, city, country });
                }
                currentTimeIndex++;
            }
        }

        drawMap();
        drawDateLabel();
        drawHover();
    };

    function drawMap() {
        p.background(0);
        p.push();
        p.translate(p.width / 2 + panX, p.height / 2 + panY);
        p.scale(gap);
        p.translate(-p.width / 2, -p.height / 2);

        hoverData = null;
        let closestDist = Infinity;

        for (const pt of cumulativePoints) {
            const lat = p.constrain(pt.lat, -MAX_LAT, MAX_LAT);
            const x = p.map(pt.lon, minLon, maxLon, 0, p.width);
            const mercY = p.log(p.tan(p.PI / 4 + p.radians(lat) / 2));
            const y = p.map(mercY, minMercY, maxMercY, p.height, 0);
            const d = p.map(pt.sif, minSIF, maxSIF, 2, 10);
            p.fill(seasonColors[pt.season]);
            p.circle(x, y, d / gap);

            const distMouse = p.dist(p.mouseX, p.mouseY, x, y);
            if (distMouse < closestDist && distMouse < 20) {
                closestDist = distMouse;
                hoverData = { ...pt, x, y };
            }
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
        ["Winter", "Spring", "Summer", "Fall"].forEach((s, i) => {
            p.fill(seasonColors[s]);
            p.rect(legendX, legendY + 15 + i * 20, 12, 12);
            p.fill(255);
            p.text(s, legendX + 20, legendY + 27 + i * 20);
        });
        p.pop();
    }

    function drawDateLabel() {
        p.push();
        p.textAlign(p.CENTER, p.TOP);
        p.fill(255);
        p.textSize(18);
        if (currentTimeIndex > 0) {
            p.text(`Date: ${times[Math.min(currentTimeIndex - 1, times.length - 1)]}`, p.width / 2, 10);
        }
        p.pop();
    }

    function drawHover() {
        if (!hoverData) return;
        p.push();
        p.fill(0, 200);
        p.stroke(255);
        p.rect(hoverData.x + 10, hoverData.y - 25, 140, 50, 5);
        p.noStroke();
        p.fill(255);
        p.textSize(12);
        p.textAlign(p.LEFT, p.TOP);
        p.text(`City: ${hoverData.city}`, hoverData.x + 15, hoverData.y - 20);
        p.text(`Country: ${hoverData.country}`, hoverData.x + 15, hoverData.y - 5);
        p.text(`SIF: ${hoverData.sif.toFixed(2)}`, hoverData.x + 15, hoverData.y + 10);
        p.pop();
    }

    p.mousePressed = () => {
        playing = !playing;
        dragging = true;
        lastMouseX = p.mouseX; lastMouseY = p.mouseY;
    };
    p.mouseDragged = () => {
        if (!dragging) return;
        panX += p.mouseX - lastMouseX;
        panY += p.mouseY - lastMouseY;
        lastMouseX = p.mouseX; lastMouseY = p.mouseY;
    };
    p.mouseReleased = () => { dragging = false; };
};

new p5(seasons_sif, 'seasons_sif');
