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

    let topColor, bottomColor;

    p.preload = () => {
        table = p.loadTable("../data/SIF_disagg_geocode_2019-2025.csv", "csv", "header");
    };

    p.setup = () => {
        const parent = document.getElementById("movingbars_sif");
        const c = p.createCanvas(parent.clientWidth, parent.clientHeight);
        c.parent(parent);

        p.textAlign(p.CENTER, p.CENTER);

        topColor = p.color(255, 80, 80);
        bottomColor = p.color(160, 0, 0);

        for (let r = 0; r < table.getRowCount(); r++) {
            let city = table.getString(r, "city");
            if (city && !cities.includes(city)) cities.push(city);
        }

        let cityMonthSIF = {};
        let monthSet = new Set();

        for (let r = 0; r < table.getRowCount(); r++) {
            let city = table.getString(r, "city");
            let v = table.getNum(r, "Daily_SIF_");
            if (!isFinite(v)) continue;
            let datetime = table.getString(r, "datetime");
            if (!datetime) continue;
            const date = new Date(datetime);
            const key = `${date.getFullYear()}-${p.nf(date.getMonth() + 1, 2)}`;
            monthSet.add(key);

            if (!cityMonthSIF[city]) cityMonthSIF[city] = {};
            if (!cityMonthSIF[city][key]) cityMonthSIF[city][key] = { sum: 0, count: 0 };
            cityMonthSIF[city][key].sum += v;
            cityMonthSIF[city][key].count += 1;
        }

        monthKeys = Array.from(monthSet).sort();
        for (let k of monthKeys) {
            const parts = k.split("-");
            months.push(`${monthName(parseInt(parts[1]))} ${parts[0]}`);
        }

        for (let city of cities) {
            let raw = cityMonthSIF[city];
            if (!raw) continue;

            let arr = [];
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

        const t = p.millis() / 10; // controls speed
        currentMonthIndex = Math.floor(t) % months.length;

        p.fill(255);
        p.textAlign(p.LEFT, p.TOP);
        p.textSize(28);
        p.text(months[currentMonthIndex], 60, 15);

        const centerY = p.height * 0.45;
        const maxDown = 300;
        const leftMargin = 80;
        const rightMargin = 40;
        const usableWidth = p.width - leftMargin - rightMargin;
        const spacing = usableWidth / Math.max(cities.length, 1);
        const barWidth = Math.min(spacing * 0.7, 14);

        barInfo = [];

        for (let i = 0; i < cities.length; i++) {
            const city = cities[i];
            const sifArr = sifSeries[city];
            if (!sifArr) continue;
            const x = leftMargin + spacing * i + spacing * 0.5;
            const sifVal = sifArr[currentMonthIndex];
            const downH = p.map(sifVal, sifMin, sifMax, 5, maxDown);

            p.fill(bottomColor);
            p.rectMode(p.CORNER);
            p.rect(x - barWidth / 2, centerY, barWidth, downH);

            barInfo.push({ city, x, barWidth, centerY, downH, sifVal });
        }

        p.stroke(255);
        p.line(0, centerY, p.width, centerY);
        p.noStroke();

        drawTooltip(p);
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
        const tipText3 = hovered.sifVal != null ? `SIF: ${p.nf(hovered.sifVal, 1, 3)}` : "";

        const w1 = p.textWidth(tipText1);
        const w3 = p.textWidth(tipText3);
        const tw = Math.max(w1, w3) + 20;
        const th = 40;

        let tx = hovered.x;
        let ty = hovered.centerY + hovered.downH + 25;
        if (tx - tw / 2 < 0) tx = tw / 2 + 5;
        if (tx + tw / 2 > p.width) tx = p.width - tw / 2 - 5;

        p.rectMode(p.CENTER);
        p.fill(255);
        p.stroke(0);
        p.rect(tx, ty, tw, th, 6);

        p.noStroke();
        p.fill(0);
        p.textAlign(p.CENTER, p.CENTER);
        let lineY = ty - 8;
        p.text(tipText1, tx, lineY);
        lineY += 16;
        if (tipText3 !== "") p.text(tipText3, tx, lineY);
    }

    function monthName(m) {
        return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m - 1];
    }
};

new p5(movingbars_sif, "movingbars_sif");
