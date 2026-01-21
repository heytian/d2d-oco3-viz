let s1 = function(p) {
  p.setup = function() {
    p.createCanvas(280, 280);
    p.background(200);
  };

  p.draw = function() {
    p.fill(255, 0, 0);
    p.ellipse(p.random(p.width), p.random(p.height), 20, 20);
  };
};

new p5(s1, 'sketch1');  // attach to div with id="sketch1"
