export function mount(sketchFn, container, size = 300) {
  return new p5((p) => {
    sketchFn(p, size);
  }, container);
}
