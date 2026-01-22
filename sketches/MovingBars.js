const MovingBars = (p) => {

    let cities = [];
    let months = [];
    let monthKeys = [];
    let currentMonthIndex = 0;

    let co2Table, sifTable;
    let co2Series = {};
    let sifSeries = {};

    let co2Min = Infinity;
    let co2Max = -Infinity;
    let sifMin = Infinity;
    let sifMax = -Infinity;

    let topColor, bottomColor;
    let barInfo = [];

    // ---------- preload ----------
    p.preload = () => {
        // ⚠ Make sure these paths are correct relative to the HTML file that loads this JS
        co2Table = p.loadTable("../data/CO2_combined.csv", "csv", "header");
        sifTable = p.loadTable("../data/SIF_combined.csv", "csv", "header");
    };

    // ---------- setup ----------
    p.setup = () => {
        const parent = document.getElementById("MovingBars");
        const c = p.createCanvas(parent.clientWidth, 700);
        c.parent(parent); // 🔑 attach canvas to div

        p.textAlign(p.CENTER, p.CENTER);

        topColor = p.color(255, 80, 80);
        bottomColor = p.color(160, 0, 0);

        let cityMonthCO2 = {};
        let cityMonthSIF = {};
        let monthSet = new Set();

        // ---------- CO2 ----------
        for (let r = 0; r < co2Table.getRowCount(); r++) {
            const city = co2Table.getString(r, "city");
            const v = co2Table.getNum(r, "xco2");
            if (!isFinite(v)) continue;

            if (!cities.includes(city)) cities.push(city);

            const key = parseMonthKey(co2Table.getString(r, "datetime"));
            monthSet.add(key);

            cityMonthCO2[city] ??= {};
            cityMonthCO2[city][key] ??= { sum: 0, count: 0 };
            cityMonthCO2[city][key].sum += v;
            cityMonthCO2[city][key].count++;
        }

        // ---------- SIF ----------
        for (let r = 0; r < sifTable.getRowCount(); r++) {
            const city = sifTable.getString(r, "city");
            const v = sifTable.getNum(r, "Daily_SIF_757nm");
            if (!isFinite(v)) continue;

            const key = parseMonthKey(sifTable.getString(r, "datetime"));
            monthSet.add(key);

            cityMonthSIF[city] ??= {};
            cityMonthSIF[city][key] ??= { sum: 0, count: 0 };
            cityMonthSIF[city][key].sum += v;
            cityMonthSIF[city][key].count++;
        }

        // ---------- build months array ----------
        monthKeys = Array.from(monthSet).sort();
        months = monthKeys.map(k => {
            const [y, m] = k.split("-");
            return `${monthName(+m)} ${y}`;
        });

        // ---------- build aligned series ----------
        for (const city of cities) {
            co2Series[city] = buildSeries(cityMonthCO2[city]);
            sifSeries[city] = buildSeries(cityMonthSIF[city]);

            for (const v of co2Series[city]) {
                if (isFinite(v)) {
                    co2Min = p.min(co2Min, v);
                    co2Max = p.max(co2Max, v);
                }
            }
            for (const v of sifSeries[city]) {
                if (isFinite(v)) {
                    sifMin = p.min(sifMin, v);
                    sifMax = p.max(sifMax, v);
                }
            }
        }

        // Fallbacks
        if (!isFinite(co2Min)) { co2Min = 400; co2Max = 430; }
        if (!isFinite(sifMin)) { sifMin = 0; sifMax = 1.5; }
    };

    // ---------- draw ----------
    p.draw = () => {
        p.background(245);
        if (!months.length) return;

        currentMonthIndex = Math.floor(p.millis() / 120) % months.length;

        p.fill(0);
        p.textAlign(p.LEFT, p.TOP);
        p.textSize(26);
        p.text(months[currentMonthIndex], 60, 15);

        const centerY = p.height * 0.45;
        const maxUp = 120;
        const maxDown = 100;

        const leftMargin = 80;
        const usableWidth = p.width - leftMargin - 40;
        const spacing = usableWidth / cities.length;
        const barWidth = Math.min(spacing * 0.7, 14);

        barInfo = [];

        for (let i = 0; i < cities.length; i++) {
            const city = cities[i];
            const x = leftMargin + spacing * i + spacing / 2;

            const co2Val = co2Series[city][currentMonthIndex];
            const sifVal = sifSeries[city][currentMonthIndex];

            if (isFinite(co2Val)) {
                const h = p.map(co2Val, co2Min, co2Max, 5, maxUp);
                p.fill(topColor);
                p.rect(x - barWidth / 2, centerY - h, barWidth, h);
            }

            if (isFinite(sifVal)) {
                const h = p.map(sifVal, sifMin, sifMax, 5, maxDown);
                p.fill(bottomColor);
                p.rect(x - barWidth / 2, centerY, barWidth, h);
            }
        }

        p.stroke(0);
        p.line(0, centerY, p.width, centerY);
        p.noStroke();
    };

    // ---------- helpers ----------
    function buildSeries(raw) {
        let arr = [];
        let last = null;
        for (let k of monthKeys) {
            const e = raw?.[k];
            if (e) last = e.sum / e.count;
            arr.push(last);
        }
        return arr;
    }

    function parseMonthKey(datetime) {
        const [m, , yy] = datetime.split(" ")[0].split("/");
        return `${2000 + +yy}-${p.nf(+m, 2)}`;
    }

    function monthName(m) {
        return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m - 1];
    }

};

new p5(MovingBars, 'MovingBars');
