const globeSketch = (p) => {
    // --- instance variables ---
    let table;
    let globeRadius = 210;
    let rotX = 0, rotY = 0;
    let dragging = false, lastX, lastY;
    let times = [], minTime, maxTime;
    let timeSlider, playButton, playing = false;
    let myFont;
    let zoom = 1;

    const CO2_MIN = 380, CO2_MAX = 450;
    const SIF_MIN = 0.0, SIF_MAX = 1.5;

    let patches = [], PATCH_COUNT = 65;
    let sifDots = [], SIF_DOT_COUNT = 260;

    let popupLeft = null, popupRight = null;
    let leftCenter, rightCenter, globeY;

    // --- preload ---
    p.preload = () => {
        table = p.loadTable("CO2.csv", "csv", "header");
        myFont = p.loadFont("Roboto.ttf");
    };

    // --- setup ---
    p.setup = () => {
        p.createCanvas(1100, 850, p.WEBGL);
        p.textFont(myFont);
        p.angleMode(p.RADIANS);

        // time array
        if (table && table.getRowCount && table.getRowCount() > 0) {
            const datetimeCol = table.getColumn("datetime");
            if (datetimeCol && datetimeCol.length > 0) {
                for (let r = 0; r < table.getRowCount(); r++) {
                    const t = new Date(table.getString(r, "datetime")).getTime();
                    if (!isNaN(t)) times.push(t);
                }
            }
        }
        if (times.length < 2) {
            const start = Date.now() - 180 * 24 * 3600 * 1000;
            for (let i = 0; i < 180; i++) times.push(start + i * 24 * 3600 * 1000);
        }
        minTime = p.min(times);
        maxTime = p.max(times);

        timeSlider = p.createSlider(minTime, maxTime, minTime, 1);
        timeSlider.position(20, p.height - 40);
        timeSlider.style("width", "680px");

        playButton = p.createButton("▶ Play");
        playButton.position(720, p.height - 44);
        playButton.mousePressed(togglePlay);

        initPatches();
        initSifDots();

        leftCenter = p.createVector(-p.width * 0.25, -20, 0);
        rightCenter = p.createVector(p.width * 0.25, -20, 0);
        globeY = -20;
    };

    // --- draw ---
    p.draw = () => {
        p.background(10);

        p.push();
        p.translate(leftCenter.x, globeY, 0);
        p.rotateX(rotX);
        p.rotateY(rotY);
        drawGraticule();
        drawGlobeBase();
        drawPatches();
        p.pop();

        p.push();
        p.translate(rightCenter.x, globeY, 0);
        p.rotateX(rotX);
        p.rotateY(rotY);
        drawGraticule();
        drawGlobeBase();
        drawSifDots();
        p.pop();

        drawCO2LegendTopLeft();
        drawSIFLegendTopRight();
        drawTimeLabel();
        drawPopupAboveLeft();
        drawPopupAboveRight();

        if (playing) advanceTime();
    };

    // --- globe ---
    function drawGlobeBase() {
        p.ambientLight(120);
        p.directionalLight(255, 255, 255, 1, 1, -1);
        p.noStroke();
        p.fill(30);
        p.sphere(globeRadius * zoom, 48, 48);
    }

    // --- patches ---
    function initPatches() {
        p.randomSeed(7);
        p.noiseSeed(7);
        patches = [];
        for (let i = 0; i < PATCH_COUNT; i++) {
            patches.push({
                seed: p.random(1e6),
                baseLat: p.random(-70, 70),
                baseLon: p.random(-180, 180),
                driftLatAmp: p.random(2, 18),
                driftLonAmp: p.random(2, 28),
                driftSpeed: p.random(0.4, 1.8),
                baseSizeDeg: p.random(2.0, 10.0),
                sizePulse: p.random(0.6, 1.6),
                irregularity: p.random(0.25, 0.7),
                segments: p.floor(p.random(10, 22)),
                valueSpeed: p.random(0.5, 2.2),
                valuePhase: p.random(p.TWO_PI),
                valueBias: p.random(-0.15, 0.25),
            });
        }
    }

    function drawPatches() {
        const t = timeSlider.value();
        const timeNorm = (t - minTime) / Math.max(1, maxTime - minTime);
        const tt = timeNorm * p.TWO_PI;
        const surfaceR = (globeRadius + 0.9) * zoom;

        const ordered = patches
            .map(patch => {
                const c = patchCenterLatLon(patch, tt);
                const pos = latLonToXYZ(p.radians(c.lat), p.radians(c.lon), surfaceR);
                return { patch, c, pos };
            })
            .sort((a, b) => a.pos.z - b.pos.z);

        p.noStroke();
        for (const item of ordered) {
            const patch = item.patch;
            const center = item.c;
            const size = patch.baseSizeDeg * (0.55 + 0.45 * p.sin(tt * patch.sizePulse + patch.seed * 0.00001 + 1.3));
            const raw = 0.5 + 0.35 * p.sin(tt * patch.valueSpeed + patch.valuePhase) +
                0.22 * (p.noise(patch.seed * 0.00001, tt * 0.35) - 0.5) +
                patch.valueBias;
            const value = p.lerp(CO2_MIN, CO2_MAX, p.constrain(raw, 0, 1));
            p.fill(co2ColorYellowRed(value));
            drawPatchPolygonOnSphere(center.lat, center.lon, size, patch.irregularity, patch.segments, surfaceR, patch.seed, tt);
        }
    }

    function patchCenterLatLon(patch, tt) {
        const lat = patch.baseLat + patch.driftLatAmp * p.sin(tt * patch.driftSpeed + patch.seed * 0.00002);
        const lon = patch.baseLon + patch.driftLonAmp * p.cos(tt * (patch.driftSpeed * 0.85) + patch.seed * 0.00003);
        return { lat: p.constrain(lat, -85, 85), lon: wrapLon(lon) };
    }

    function drawPatchPolygonOnSphere(centerLatDeg, centerLonDeg, sizeDeg, irregularity, segments, r, seed, tt) {
        const lat0 = p.radians(centerLatDeg);
        p.beginShape(p.TRIANGLE_FAN);
        const c = latLonToXYZ(p.radians(centerLatDeg), p.radians(centerLonDeg), r);
        p.vertex(c.x, c.y, c.z);

        for (let i = 0; i <= segments; i++) {
            const a = (i / segments) * p.TWO_PI;
            const n = p.noise(seed * 0.00001 + p.cos(a) * 0.7, seed * 0.00002 + p.sin(a) * 0.7, tt * 0.18);
            const rad = sizeDeg * (1.0 + irregularity * (n - 0.5) * 2.0);
            const dLat = rad * p.cos(a);
            const cosLat = Math.max(0.15, Math.abs(p.cos(lat0)));
            const dLon = (rad * p.sin(a)) / cosLat;
            const lat = p.constrain(centerLatDeg + dLat, -88, 88);
            const lon = wrapLon(centerLonDeg + dLon);
            const pxyz = latLonToXYZ(p.radians(lat), p.radians(lon), r);
            p.vertex(pxyz.x, pxyz.y, pxyz.z);
        }
        p.endShape();
    }

    // --- SIF dots ---
    function initSifDots() {
        p.randomSeed(11);
        p.noiseSeed(11);
        sifDots = [];
        for (let i = 0; i < SIF_DOT_COUNT; i++) {
            sifDots.push({
                seed: p.random(1e6),
                baseLat: p.random(-75, 75),
                baseLon: p.random(-180, 180),
                driftLatAmp: p.random(0.5, 8),
                driftLonAmp: p.random(0.5, 12),
                driftSpeed: p.random(0.6, 2.4),
                valueSpeed: p.random(0.6, 2.8),
                valuePhase: p.random(p.TWO_PI),
                baseSize: p.random(2, 6),
                sizePulse: p.random(0.6, 2.0),
            });
        }
    }

    function drawSifDots() {
        const t = timeSlider.value();
        const timeNorm = (t - minTime) / Math.max(1, maxTime - minTime);
        const tt = timeNorm * p.TWO_PI;
        const r = (globeRadius + 2.0) * zoom;

        const ordered = sifDots
            .map(d => {
                const c = sifDotLatLon(d, tt);
                const pos = latLonToXYZ(p.radians(c.lat), p.radians(c.lon), r);
                return { d, c, pos };
            })
            .sort((a, b) => a.pos.z - b.pos.z);

        for (const item of ordered) {
            const d = item.d;
            const pos = item.pos;
            const raw = 0.55 + 0.35 * p.sin(tt * d.valueSpeed + d.valuePhase) +
                0.25 * (p.noise(d.seed * 0.00002, tt * 0.25) - 0.5);
            const sif = p.lerp(SIF_MIN, SIF_MAX, p.constrain(raw, 0, 1));
            const size = d.baseSize * (0.65 + 0.35 * p.sin(tt * d.sizePulse + d.seed * 0.00001));
            p.strokeWeight(size * zoom);
            p.stroke(sifColorBlueGreen(sif));
            p.point(pos.x, pos.y, pos.z);
        }
    }

    function sifDotLatLon(d, tt) {
        const lat = d.baseLat + d.driftLatAmp * p.sin(tt * d.driftSpeed + d.seed * 0.00002);
        const lon = d.baseLon + d.driftLonAmp * p.cos(tt * (d.driftSpeed * 0.9) + d.seed * 0.00003);
        return { lat: p.constrain(lat, -85, 85), lon: wrapLon(lon) };
    }

    // --- mouse interactions ---
    p.mousePressed = () => { dragging = true; lastX = p.mouseX; lastY = p.mouseY; };
    p.mouseReleased = () => { dragging = false; };
    p.mouseDragged = () => {
        const sliderTop = p.height - 60;
        if (p.mouseY > sliderTop || !dragging) return;
        rotY += (p.mouseX - lastX) * 0.005;
        rotX += (p.mouseY - lastY) * 0.005;
        rotX = p.constrain(rotX, -p.PI / 2, p.PI / 2);
        lastX = p.mouseX;
        lastY = p.mouseY;
    };
    p.mouseWheel = (event) => {
        zoom -= event.delta * 0.001;
        zoom = p.constrain(zoom, 0.5, 2);
    };

    function togglePlay() { playing = !playing; playButton.html(playing ? "❚❚ Pause" : "▶ Play"); }
    function advanceTime() {
        let t = timeSlider.value();
        t += (maxTime - minTime) / 600;
        if (t > maxTime) t = minTime;
        timeSlider.value(t);
    }

    // --- helpers ---
    function wrapLon(lon) { while (lon > 180) lon -= 360; while (lon < -180) lon += 360; return lon; }
    function latLonToXYZ(lat, lon, r) {
        const x = r * p.cos(lat) * p.sin(lon);
        const y = -r * p.sin(lat);
        const z = r * p.cos(lat) * p.cos(lon);
        return { x, y, z };
    }
    function co2ColorYellowRed(value) {
        const t = p.constrain(p.map(value, CO2_MIN, CO2_MAX, 0, 1), 0, 1);
        const c1 = p.color(255, 245, 170), c2 = p.color(255, 220, 90);
        const c3 = p.color(255, 165, 50), c4 = p.color(235, 70, 60), c5 = p.color(150, 0, 0);
        if (t < 0.25) return p.lerpColor(c1, c2, t / 0.25);
        if (t < 0.55) return p.lerpColor(c2, c3, (t - 0.25) / 0.3);
        if (t < 0.82) return p.lerpColor(c3, c4, (t - 0.55) / 0.27);
        return p.lerpColor(c4, c5, (t - 0.82) / 0.18);
    }
    function sifColorBlueGreen(value) {
        const t = p.constrain(p.map(value, SIF_MIN, SIF_MAX, 0, 1), 0, 1);
        const c1 = p.color(30, 90, 255), c2 = p.color(40, 200, 220), c3 = p.color(60, 220, 120);
        if (t < 0.5) return p.lerpColor(c1, c2, t / 0.5);
        return p.lerpColor(c2, c3, (t - 0.5) / 0.5);
    }

    // --- graticule ---
    function drawGraticule() {
        p.stroke(120, 120, 120, 80);
        p.noFill();
        const r = (globeRadius + 1) * zoom;
        for (let lat = -75; lat <= 75; lat += 15) {
            p.beginShape();
            for (let lon = -180; lon <= 180; lon += 5) p.vertex(latLonToXYZ(p.radians(lat), p.radians(lon), r).x, latLonToXYZ(p.radians(lat), p.radians(lon), r).y, latLonToXYZ(p.radians(lat), p.radians(lon), r).z);
            p.endShape();
        }
        for (let lon = -180; lon < 180; lon += 15) {
            p.beginShape();
            for (let lat = -90; lat <= 90; lat += 5) p.vertex(latLonToXYZ(p.radians(lat), p.radians(lon), r).x, latLonToXYZ(p.radians(lat), p.radians(lon), r).y, latLonToXYZ(p.radians(lat), p.radians(lon), r).z);
            p.endShape();
        }
    }

    // --- TODO: Legends, Popups, MiniCharts ---
    // Use the same pattern: `p.fill`, `p.rect`, `p.text`, etc., fully inside the instance.
};

new p5(globeSketch, "globeContainer");
