# Findings

- Error message when loading a texture without kn.init() is misleading
- Window.create extremely picky regarding the width/height types.
    - no unpacking of Vector2
    - no floats

- Vec2 can't be initialized by ints?!?
- Docs for time.get_delta() say "not smaller than 1/12s", while it should be "not larger than..."
- event needs a proper repr showing its fields
- Missing container type for angle/pivot.  It should be somehow either be
  bundled with the Transform, or the Texture
