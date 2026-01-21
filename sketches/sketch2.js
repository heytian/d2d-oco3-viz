let s2 = function(p) {
  p.setup = function() {
    p.createCanvas(280, 280);
    p.background(50, 100, 200);
  };

  p.draw = function() {
    p.fill(255);
    p.rect(p.random(p.width), p.random(p.height), 30, 30);
  };
};

new p5(s2, 'sketch2');  // attach to div with id="sketch2"
