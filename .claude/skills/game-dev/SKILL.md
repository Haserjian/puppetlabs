---
name: game-development
description: Game development patterns, game loops, physics, ECS architecture, and game engine concepts. Use when building games, implementing game mechanics, or working with game engines.
---

# Game Development Skill

## When to Use
- Implementing game mechanics
- Building game loops and update cycles
- Working with physics systems
- Designing entity-component systems
- Optimizing game performance

## Core Game Loop
```python
def game_loop():
    while running:
        # 1. Process input
        handle_input()

        # 2. Update game state (fixed timestep)
        accumulator += delta_time
        while accumulator >= FIXED_DT:
            update_physics(FIXED_DT)
            accumulator -= FIXED_DT

        # 3. Render (variable timestep)
        interpolation = accumulator / FIXED_DT
        render(interpolation)

        # 4. Frame timing
        delta_time = clock.tick(TARGET_FPS)
```

## Entity-Component-System (ECS)
```python
# Components = Pure data
@dataclass
class Position:
    x: float
    y: float

@dataclass
class Velocity:
    dx: float
    dy: float

# Systems = Logic that operates on components
def movement_system(world, dt):
    for entity in world.query(Position, Velocity):
        pos, vel = entity.get(Position, Velocity)
        pos.x += vel.dx * dt
        pos.y += vel.dy * dt

# Entities = Just IDs with attached components
player = world.create_entity()
world.add(player, Position(0, 0), Velocity(1, 0))
```

## Physics Patterns

### Collision Detection
1. **Broad phase** - Spatial partitioning (grid, quadtree, BVH)
2. **Narrow phase** - Precise shape intersection
3. **Resolution** - Separate objects, apply impulses

### Common Collision Shapes
- AABB (Axis-Aligned Bounding Box) - Fast, simple
- Circle/Sphere - Fast, rotation invariant
- OBB (Oriented Bounding Box) - More accurate
- Convex hull - Complex shapes
- Mesh colliders - Last resort, expensive

## Game Math Essentials
```python
# Vector operations
def normalize(v): return v / length(v)
def dot(a, b): return a.x*b.x + a.y*b.y
def reflect(v, n): return v - 2*dot(v,n)*n

# Interpolation
def lerp(a, b, t): return a + (b-a)*t
def smoothstep(t): return t*t*(3-2*t)

# Angles
def angle_to_vector(angle): return (cos(angle), sin(angle))
def vector_to_angle(v): return atan2(v.y, v.x)
```

## Performance Optimization
1. **Object pooling** - Reuse objects instead of allocating
2. **Spatial partitioning** - Only check nearby objects
3. **LOD (Level of Detail)** - Simplify distant objects
4. **Culling** - Don't process/render off-screen
5. **Data-oriented design** - Cache-friendly memory layout

## Game Balance Principles
- **Feedback loops** - Positive (snowball) vs negative (catch-up)
- **Risk/reward** - Higher risk = higher reward
- **Meaningful choices** - No dominant strategies
- **Emergence** - Simple rules, complex outcomes
- **Pacing** - Tension and release cycles

## Common Architectures
- **State machines** - Character states (idle, walk, jump)
- **Behavior trees** - AI decision making
- **Event systems** - Decoupled communication
- **Command pattern** - Input handling, replays, undo

## Testing Games
- Deterministic replay systems
- Automated playtesting bots
- Performance profiling
- Memory leak detection
- Stress testing with many entities
