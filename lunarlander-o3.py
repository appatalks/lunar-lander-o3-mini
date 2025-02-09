import pygame
import math
import sys
import random

# Screen settings
WIDTH, HEIGHT = 1200, 800
FPS = 60

# Colors
WHITE   = (255, 255, 255)
BLACK   = (0, 0, 0)
GREEN   = (0, 200, 0)
RED     = (200, 0, 0)
GRAY    = (100, 100, 100)
YELLOW  = (255, 255, 0)

# ---------------------------
# Helper Functions
# ---------------------------
def get_terrain_height(x, terrain_points, step=20):
    """
    Given an x coordinate, linearly interpolate the y value from terrain_points.
    terrain_points: list of (x, y) with x spaced by 'step'.
    """
    if x <= 0:
        return terrain_points[0][1]
    if x >= WIDTH:
        return terrain_points[-1][1]
    idx = int(x // step)
    p1 = terrain_points[idx]
    p2 = terrain_points[min(idx+1, len(terrain_points)-1)]
    t = (x - p1[0]) / (p2[0] - p1[0])
    return p1[1] * (1-t) + p2[1] * t

def smooth_terrain(points, iterations=2):
    """Simple moving average smoothing for a list of (x, y) points."""
    for _ in range(iterations):
        new_points = [points[0]]
        for i in range(1, len(points)-1):
            avg_y = (points[i-1][1] + points[i][1] + points[i+1][1]) / 3
            new_points.append((points[i][0], avg_y))
        new_points.append(points[-1])
        points = new_points
    return points

def generate_terrain_and_landing_zones():
    """
    Generates a random terrain (a list of (x, y) points) and inserts several
    flat landing pads at random x-locations. Returns (terrain_points, landing_zones)
    """
    step = 20
    # Generate rough terrain points along the width.
    terrain_points = []
    for x in range(0, WIDTH + 1, step):
        # y between HEIGHT-300 and HEIGHT-100
        y = random.randint(HEIGHT - 300, HEIGHT - 100)
        terrain_points.append((x, y))
    terrain_points = smooth_terrain(terrain_points, iterations=3)

    landing_zones = []
    num_zones = 3
    attempts = 0
    used_zones = []  # to avoid overlapping pads

    while len(landing_zones) < num_zones and attempts < 20:
        attempts += 1
        pad_width = random.randint(80, 150)
        pad_x = random.randint(50, WIDTH - pad_width - 50)
        pad_right = pad_x + pad_width

        # Check overlap with previously placed landing zones.
        overlap = False
        for zone in used_zones:
            if not (pad_right < zone[0] or pad_x > zone[1]):
                overlap = True
                break
        if overlap:
            continue

        # Determine landing pad y by sampling terrain_points over [pad_x, pad_right]
        samples = []
        for x in range(pad_x, pad_right + 1, step):
            samples.append(get_terrain_height(x, terrain_points, step))
        if not samples:
            continue
        pad_y = sum(samples) / len(samples)
        # Flatten the terrain in this segment:
        for i, (tx, ty) in enumerate(terrain_points):
            if pad_x <= tx <= pad_right:
                terrain_points[i] = (tx, pad_y)
        # Create a landing zone rectangle (a little thicker than the flat surface)
        pad_thickness = 10
        zone_rect = pygame.Rect(pad_x, int(pad_y - pad_thickness), pad_width, pad_thickness)
        landing_zones.append(LandingZone(zone_rect.x, zone_rect.y, zone_rect.width, zone_rect.height, maxLandingSpeed=2, label="Pad"))
        used_zones.append((pad_x, pad_right))
    return terrain_points, landing_zones

def custom_gravity_input(screen, clock, font):
    """
    Display a simple text prompt for the user to type in a custom gravity value.
    Returns the gravity as a float.
    """
    input_str = ""
    prompt = "Enter custom gravity (e.g., 0.1) and press Enter:"
    while True:
        screen.fill(BLACK)
        prompt_surf = font.render(prompt, True, WHITE)
        input_surf = font.render(input_str, True, YELLOW)
        screen.blit(prompt_surf, (50, HEIGHT//2 - 50))
        screen.blit(input_surf, (50, HEIGHT//2))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    try:
                        val = float(input_str)
                        return val
                    except ValueError:
                        input_str = ""
                elif event.key == pygame.K_BACKSPACE:
                    input_str = input_str[:-1]
                else:
                    input_str += event.unicode
        clock.tick(FPS)

# ---------------------------
# Game Object Classes
# ---------------------------
class Lander:
    def __init__(self, gravity=0.1):
        self.x = WIDTH // 2
        self.y = 100  # starting height
        self.vx = 0
        self.vy = 0
        self.angle = 0          # in degrees (0 => facing up)
        self.fuel = 100.0
        self.gravity = gravity  # planet-specific gravity
        self.thrust = 0.2       # acceleration when thrusting
        self.fuelConsumptionRate = 20  # units per second

    def update(self, dt, thrusting):
        # Gravity always applies
        self.vy += self.gravity
        # Thrust if available
        if thrusting and self.fuel > 0:
            rad = math.radians(self.angle)
            ax = -self.thrust * math.sin(rad)
            ay = -self.thrust * math.cos(rad)
            self.vx += ax
            self.vy += ay
            self.fuel -= self.fuelConsumptionRate * dt
            if self.fuel < 0:
                self.fuel = 0
        self.x += self.vx
        self.y += self.vy

    def draw(self, surface):
        # Draw lander as a triangle
        rad = math.radians(self.angle)
        size = 20
        tip = (self.x - math.sin(rad)*size, self.y - math.cos(rad)*size)
        left = (self.x + math.sin(rad + math.radians(120))*size,
                self.y + math.cos(rad + math.radians(120))*size)
        right = (self.x + math.sin(rad - math.radians(120))*size,
                 self.y + math.cos(rad - math.radians(120))*size)
        pygame.draw.polygon(surface, WHITE, [tip, left, right])

    def get_rect(self):
        # Bounding box for collision (centered on (x,y))
        return pygame.Rect(self.x - 15, self.y - 15, 30, 30)

class LandingZone:
    def __init__(self, x, y, width, height, maxLandingSpeed, label="Landing Zone"):
        self.rect = pygame.Rect(x, y, width, height)
        self.maxLandingSpeed = maxLandingSpeed
        self.label = label

    def draw(self, surface, font):
        pygame.draw.rect(surface, GREEN, self.rect)
        label_surf = font.render(self.label, True, BLACK)
        surface.blit(label_surf, (self.rect.x + (self.rect.width - label_surf.get_width()) // 2,
                                  self.rect.y - 25))

# ---------------------------
# Main Game Function
# ---------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Modern Lunar Lander")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20)
    large_font = pygame.font.SysFont("Arial", 32)

    game_state = "menu"  # states: menu, playing, landed, crashed
    score = 0
    selected_planet = None
    gravity = 0.1  # default

    # ---------------------------
    # Menu / Instruction Screen
    # ---------------------------
    while game_state == "menu":
        screen.fill(BLACK)
        instructions = [
            "Welcome to Modern Lunar Lander!",
            "",
            "Instructions:",
            " - LEFT/RIGHT arrow keys: rotate the lander.",
            " - SPACE: thrust (uses fuel).",
            " - Land gently on a flat pad marked in GREEN.",
            " - Avoid crashing on the rugged terrain.",
            "",
            "Select a planet option:",
            " 1: Moon    (Gravity: 0.10)",
            " 2: Mars    (Gravity: 0.15)",
            " 3: Europa  (Gravity: 0.08)",
            " 4: Random  (Gravity: random between 0.05 and 0.2)",
            " 5: Custom  (Input your own gravity)"
        ]
        for i, line in enumerate(instructions):
            text_surf = font.render(line, True, WHITE)
            screen.blit(text_surf, (50, 50 + i * 30))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    selected_planet = "Moon"
                    gravity = 0.10
                    game_state = "playing"
                elif event.key == pygame.K_2:
                    selected_planet = "Mars"
                    gravity = 0.15
                    game_state = "playing"
                elif event.key == pygame.K_3:
                    selected_planet = "Europa"
                    gravity = 0.08
                    game_state = "playing"
                elif event.key == pygame.K_4:
                    selected_planet = "Random"
                    gravity = random.uniform(0.05, 0.2)
                    game_state = "playing"
                elif event.key == pygame.K_5:
                    selected_planet = "Custom"
                    gravity = custom_gravity_input(screen, clock, font)
                    game_state = "playing"
        clock.tick(FPS)

    # ---------------------------
    # Generate the Map
    # ---------------------------
    terrain_points, landing_zones = generate_terrain_and_landing_zones()

    # ---------------------------
    # Initialize the Lander
    # ---------------------------
    lander = Lander(gravity)

    # ---------------------------
    # Main Game Loop
    # ---------------------------
    while True:
        dt = clock.tick(FPS) / 1000.0  # delta time in seconds

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # Restart game if landed or crashed:
            if game_state in ["landed", "crashed"]:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    main()  # restart
                    return

        keys = pygame.key.get_pressed()
        if game_state == "playing":
            # Rotate lander:
            if keys[pygame.K_LEFT]:
                lander.angle += 100 * dt  # degrees per second
            if keys[pygame.K_RIGHT]:
                lander.angle -= 100 * dt

            thrusting = keys[pygame.K_SPACE]
            lander.update(dt, thrusting)

            # Check boundaries so the lander stays on screen:
            if lander.x < 0: lander.x = 0
            if lander.x > WIDTH: lander.x = WIDTH

            # Collision detection with terrain:
            # Use the lander's center x to get terrain height
            ground_y = get_terrain_height(lander.x, terrain_points)
            lander_bottom = lander.y + 15  # from get_rect()
            if lander_bottom >= ground_y:
                # Check if over any landing zone:
                in_zone = None
                for lz in landing_zones:
                    if lz.rect.left <= lander.x <= lz.rect.right:
                        in_zone = lz
                        break
                speed = math.hypot(lander.vx, lander.vy)
                if in_zone and speed <= in_zone.maxLandingSpeed:
                    bonus = max(0, int((in_zone.maxLandingSpeed - speed) * 50))
                    score += int(lander.fuel) + bonus
                    game_state = "landed"
                else:
                    game_state = "crashed"
                # Stop motion on collision
                lander.vx = lander.vy = 0

        # ---------------------------
        # Drawing
        # ---------------------------
        screen.fill(BLACK)

        # Draw terrain as a polygon:
        terrain_poly = [(0, HEIGHT)] + terrain_points + [(WIDTH, HEIGHT)]
        pygame.draw.polygon(screen, GRAY, terrain_poly)

        # Draw landing zones:
        for lz in landing_zones:
            lz.draw(screen, font)

        # Draw the lander:
        lander.draw(screen)

        # HUD: fuel, score, planet info
        fuel_text = font.render(f"Fuel: {int(lander.fuel)}", True, WHITE)
        score_text = font.render(f"Score: {score}", True, WHITE)
        planet_text = font.render(f"Planet: {selected_planet} (Gravity: {gravity:.2f})", True, WHITE)
        screen.blit(fuel_text, (10, 10))
        screen.blit(score_text, (10, 40))
        screen.blit(planet_text, (10, 70))

        if game_state == "landed":
            msg = large_font.render("Successful Landing! Press R to restart", True, GREEN)
            screen.blit(msg, ((WIDTH - msg.get_width()) // 2, HEIGHT // 2))
        elif game_state == "crashed":
            msg = large_font.render("Crash Landing! Press R to restart", True, RED)
            screen.blit(msg, ((WIDTH - msg.get_width()) // 2, HEIGHT // 2))

        pygame.display.flip()

if __name__ == "__main__":
    main()
