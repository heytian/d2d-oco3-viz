const sketch1 = (p) => {
    p.setup = () => {
        const c = p.createCanvas(300, 300);
        c.parent("sketch1");
    };

    p.draw = () => {
        p.background(220);
        p.circle(p.mouseX, p.mouseY, 20);
    };
};

new p5(sketch1);
