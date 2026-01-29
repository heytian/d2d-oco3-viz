// WIP. To change from countries to city next. dd Jan 29 1455h

const movingbars_sif = (p) => {
    let table;
    let cities = [];
    let months = [];
    let monthKeys = [];
    let currentMonthIndex = 0;

    let sifSeries = {};
    let sifMin = 0;
    let sifMax = 1.5;

    let barInfo = [];
    let animationRunning = true;

    let countryFilter = new Set();
    let minPop = 0;
    let seasonFilter = { Winter: true, Spring: true, Summer: true, Fall: true };

    let countryMultiselect;
    let minPopSlider, minPopLabel;
    let seasonCheckboxes = {};

    let sortOrder = "original";
    let sortButtons = {};

    let cityMeta = {};

    const seasonColorsNH = { Winter: [0, 150, 255], Spring: [0, 255, 0], Summer: [255, 165, 0], Fall: [255, 0, 0] };
    const seasonColorsSH = { Winter: [255, 165, 0], Spring: [255, 0, 0], Summer: [0, 150, 255], Fall: [0, 255, 0] };

    p.preload = () => {
        table = p.loadTable("../data/SIF_olympic.csv", "csv", "header");
    };

    p.setup = () => {
        const parent = document.getElementById("movingbars_sif");
        const c = p.createCanvas(parent.clientWidth, parent.clientHeight);
        c.parent(parent);
        p.textAlign(p.CENTER, p.CENTER);

        let cityMonthSIF = {};
        let monthSet = new Set();

        for (let r = 0; r < table.getRowCount(); r++) {
            const city = table.getString(r, "city");
            const country = table.getString(r, "country");
            if (!city || !country) continue;

            const v = table.getNum(r, "Daily_SIF_");
            if (!isFinite(v) || v < 0) continue;

            const datetime = table.getString(r, "datetime");
            if (!datetime) continue;

            if (!cities.includes(city)) {
                cities.push(city);
                cityMeta[city] = {
                    country: country,
                    latitude: table.getNum(r, "latitude") || 0,
                    population: table.getNum(r, "j_POP_MAX") || 0
                };
            }

            const date = new Date(datetime);
            const key = `${date.getFullYear()}-${p.nf(date.getMonth() + 1, 2)}-${p.nf(date.getDate(), 2)}`;
            monthSet.add(key);

            if (!cityMonthSIF[city]) cityMonthSIF[city] = {};
            if (!cityMonthSIF[city][key]) cityMonthSIF[city][key] = { sum: 0, count: 0 };
            cityMonthSIF[city][key].sum += v;
            cityMonthSIF[city][key].count += 1;
        }

        monthKeys = Array.from(monthSet).sort();
        for (let k of monthKeys) {
            const parts = k.split("-");
            months.push(`${parts[2]} ${monthName(parseInt(parts[1]))} ${parts[0]}`);
        }

        for (let city of cities) {
            const raw = cityMonthSIF[city];
            if (!raw) continue;

            const arr = [];
            let lastVal = null;
            for (let i = 0; i < monthKeys.length; i++) {
                const key = monthKeys[i];
                const entry = raw[key];
                let value = null;
                if (entry) {
                    value = entry.sum / entry.count;
                    lastVal = value;
                } else if (lastVal !== null) {
                    value = lastVal;
                }
                arr[i] = value;
            }

            let firstIdx = arr.findIndex(v => v != null);
            if (firstIdx > 0) {
                for (let i = 0; i < firstIdx; i++) arr[i] = arr[firstIdx];
            }

            let current = arr[firstIdx];
            for (let i = firstIdx; i < arr.length; i++) {
                if (arr[i] == null) arr[i] = current;
                else current = arr[i];
            }

            sifSeries[city] = arr;
        }


        const countries = Array.from(new Set(cities.map(c => cityMeta[c].country))).sort();
        countryMultiselect = p.createSelect();
        countryMultiselect.parent(parent);
        countryMultiselect.position(p.width - 410, 40);
        countryMultiselect.option("All");
        countryMultiselect.attribute("multiple", true);
        countries.forEach(c => countryMultiselect.option(c));
        countryMultiselect.changed(() => {
            const selected = Array.from(countryMultiselect.selected());
            if (selected.length === 0 || selected.includes("All")) countryFilter = new Set();
            else countryFilter = new Set(selected);
        });

        const popVals = cities.map(c => cityMeta[c].population);
        const popMinVal = Math.min(...popVals);
        const popMaxVal = Math.max(...popVals);

        minPopSlider = p.createSlider(popMinVal, popMaxVal, popMinVal);
        minPopSlider.parent(parent);
        minPopSlider.position(p.width - 350, 120);
        minPopLabel = p.createDiv(`Population >= ${minPopSlider.value()}`);
        minPopLabel.parent(parent);
        minPopLabel.position(p.width - 340, 145);
        minPopLabel.style('color', 'white');
        minPopSlider.input(() => {
            minPop = minPopSlider.value();
            minPopLabel.html(`Population >= ${minPop}`);
        });

        // const seasonNames = ["Winter", "Spring", "Summer", "Fall"];
        // seasonNames.forEach((s, i) => {
        //     const cb = p.createCheckbox(s, true);
        //     cb.parent(parent);
        //     cb.position(30 + i * 90, 100);
        //     cb.changed(() => { seasonFilter[s] = cb.checked(); });
        //     cb.style('color', 'white');
        //     seasonCheckboxes[s] = cb;
        // });

        sortButtons.asc = p.createButton("Sort Asc");
        sortButtons.asc.parent(parent);
        sortButtons.asc.position(30, 130);
        sortButtons.asc.mousePressed(() => sortOrder = "asc");

        sortButtons.desc = p.createButton("Sort Desc");
        sortButtons.desc.parent(parent);
        sortButtons.desc.position(100, 130);
        sortButtons.desc.mousePressed(() => sortOrder = "desc");

        sortButtons.original = p.createButton("Original Order");
        sortButtons.original.parent(parent);
        sortButtons.original.position(200, 130);
        sortButtons.original.mousePressed(() => sortOrder = "original");

        p.noStroke();
    };

    p.draw = () => {
        p.background(0);

        if (months.length === 0) {
            p.fill(255);
            p.textSize(24);
            p.text("No data loaded", p.width / 2, p.height / 2);
            return;
        }

        if (animationRunning) {
            const t = p.millis() / 10;
            currentMonthIndex = Math.floor(t) % months.length;
        }

        p.fill(255);
        p.textAlign(p.LEFT, p.TOP);
        p.textSize(20);
        p.text(months[currentMonthIndex], 60, 15);

        const centerY = p.height * 0.45;
        const maxDown = 300;
        const leftMargin = 80;
        const rightMargin = 40;

        let displayCities = cities.filter(city => {
            const meta = cityMeta[city];
            if (countryFilter.size && !countryFilter.has(meta.country)) return false;
            if (meta.population < minPop) return false;
            return true;
        });

        if (sortOrder === "asc") displayCities.sort((a, b) => sifSeries[a][currentMonthIndex] - sifSeries[b][currentMonthIndex]);
        else if (sortOrder === "desc") displayCities.sort((a, b) => sifSeries[b][currentMonthIndex] - sifSeries[a][currentMonthIndex]);

        const spacing = (p.width - leftMargin - rightMargin) / Math.max(displayCities.length, 1);
        const barWidth = Math.min(spacing * 0.7, 14);

        barInfo = [];

        for (let i = 0; i < displayCities.length; i++) {
            const city = displayCities[i];
            const sifArr = sifSeries[city];
            const meta = cityMeta[city];
            const x = leftMargin + spacing * i + spacing * 0.5;
            const sifVal = sifArr[currentMonthIndex];
            const downH = p.map(sifVal, sifMin, sifMax, 5, maxDown);

            const dateParts = monthKeys[currentMonthIndex].split("-");
            const month = parseInt(dateParts[1]) - 1;
            let season = month <= 1 || month === 11 ? "Winter" :
                month <= 4 ? "Spring" :
                    month <= 7 ? "Summer" : "Fall";

            if (!seasonFilter[season]) continue;

            const colorArr = meta.latitude >= 0 ? seasonColorsNH[season] : seasonColorsSH[season];

            p.fill(colorArr);
            p.rectMode(p.CORNER);
            p.rect(x - barWidth / 2, centerY, barWidth, downH);

            barInfo.push({ city, x, barWidth, centerY, downH, sifVal, season });
        }

        p.stroke(255);
        p.line(0, centerY, p.width, centerY);
        p.noStroke();

        drawTooltip(p);
        drawSeasonLegend(p);
    };

    function drawTooltip(p) {
        let hovered = null;
        for (let info of barInfo) {
            const x1 = info.x - info.barWidth / 2;
            const x2 = info.x + info.barWidth / 2;
            const yTop = info.centerY;
            const yBottom = info.centerY + info.downH;
            if (p.mouseX >= x1 && p.mouseX <= x2 && p.mouseY >= yTop && p.mouseY <= yBottom) {
                hovered = info;
                break;
            }
        }

        if (!hovered) return;

        const tipText1 = hovered.city;
        const tipText2 = cityMeta[hovered.city].country;
        const tipText3 = hovered.sifVal != null ? `SIF: ${p.nf(hovered.sifVal, 1, 3)}` : "";

        const w1 = p.textWidth(tipText1);
        const w2 = p.textWidth(tipText2);
        const w3 = p.textWidth(tipText3);
        const tw = Math.max(w1, w2, w3) + 20;
        const th = 60;

        let tx = hovered.x;
        let ty = hovered.centerY + hovered.downH + 30;
        if (tx - tw / 2 < 0) tx = tw / 2 + 5;
        if (tx + tw / 2 > p.width) tx = p.width - tw / 2 - 5;

        p.rectMode(p.CENTER);
        p.fill(255);
        p.stroke(0);
        p.rect(tx, ty, tw, th, 6);

        p.noStroke();
        p.fill(0);
        p.textAlign(p.CENTER, p.CENTER);
        let lineY = ty - 12;
        p.text(tipText1, tx, lineY);
        lineY += 16;
        p.text(tipText2, tx, lineY);
        lineY += 16;
        if (tipText3 !== "") p.text(tipText3, tx, lineY);
    }

    function drawSeasonLegend(p) {
        const seasons = ["Winter", "Spring", "Summer", "Fall"];
        const startX = p.width - 180;
        const startY = 20;
        p.textSize(14);
        p.textAlign(p.LEFT, p.CENTER);
        seasons.forEach((s, i) => {
            p.fill(seasonColorsNH[s]);
            p.rect(startX, startY + i * 20, 12, 12);
            p.fill(255);
            p.text(s, startX + 20, startY + i * 20 + 6);
        });
    }

    p.mousePressed = () => {
        animationRunning = !animationRunning;
    };

    function monthName(m) {
        return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m - 1];
    }
};

new p5(movingbars_sif, "movingbars_sif");
