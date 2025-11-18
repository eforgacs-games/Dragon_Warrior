import random
from pygame import Surface, display, time, font
from pygame.time import get_ticks

from src.common import BLACK, WHITE, RED


class DamageNumber:
    """Floating damage number that rises and fades out."""
    def __init__(self, damage, x, y, color=WHITE):
        self.damage = damage
        self.x = x
        self.y = y
        self.start_y = y
        self.color = color
        self.start_time = get_ticks()
        self.lifetime = 1000  # milliseconds
        self.is_alive = True

    def update(self):
        """Update position and check if still alive."""
        elapsed = get_ticks() - self.start_time
        if elapsed >= self.lifetime:
            self.is_alive = False
            return

        # Rise upward
        progress = elapsed / self.lifetime
        self.y = self.start_y - (progress * 30)  # Rise 30 pixels over lifetime

    def draw(self, screen):
        """Draw the damage number with fading."""
        if not self.is_alive:
            return

        elapsed = get_ticks() - self.start_time
        progress = elapsed / self.lifetime
        alpha = int(255 * (1 - progress))  # Fade out

        # Create font and render text
        damage_font = font.Font(None, 24)
        text_surface = damage_font.render(str(self.damage), True, self.color)
        text_surface.set_alpha(alpha)
        screen.blit(text_surface, (int(self.x), int(self.y)))


class Particle:
    """Single particle for spell effects."""
    def __init__(self, x, y, color, velocity_x=0, velocity_y=0, lifetime=500):
        self.x = x
        self.y = y
        self.color = color
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.start_time = get_ticks()
        self.lifetime = lifetime
        self.is_alive = True
        self.size = random.randint(2, 4)

    def update(self):
        """Update particle position."""
        elapsed = get_ticks() - self.start_time
        if elapsed >= self.lifetime:
            self.is_alive = False
            return

        self.x += self.velocity_x
        self.y += self.velocity_y
        self.velocity_y += 0.2  # Gravity

    def draw(self, screen):
        """Draw the particle."""
        if not self.is_alive:
            return

        elapsed = get_ticks() - self.start_time
        progress = elapsed / self.lifetime
        alpha = int(255 * (1 - progress))

        # Draw as a small colored rectangle
        particle_surface = Surface((self.size, self.size))
        particle_surface.fill(self.color)
        particle_surface.set_alpha(alpha)
        screen.blit(particle_surface, (int(self.x), int(self.y)))


class ParticleSystem:
    """Manages multiple particles for spell effects."""
    def __init__(self):
        self.particles = []

    def add_burst(self, x, y, color, count=10):
        """Create a burst of particles."""
        for _ in range(count):
            velocity_x = random.uniform(-2, 2)
            velocity_y = random.uniform(-4, -1)
            particle = Particle(x, y, color, velocity_x, velocity_y)
            self.particles.append(particle)

    def update(self):
        """Update all particles and remove dead ones."""
        for particle in self.particles:
            particle.update()
        self.particles = [p for p in self.particles if p.is_alive]

    def draw(self, screen):
        """Draw all particles."""
        for particle in self.particles:
            particle.draw(screen)

    def is_active(self):
        """Check if any particles are still alive."""
        return len(self.particles) > 0


def screen_shake(camera, intensity=5, duration=200):
    """
    Apply screen shake effect to the camera.
    @param camera: The camera object to shake
    @param intensity: Maximum pixel offset for shake
    @param duration: Duration of shake in milliseconds
    """
    start_time = get_ticks()
    original_x = camera.x
    original_y = camera.y

    while get_ticks() - start_time < duration:
        progress = (get_ticks() - start_time) / duration
        current_intensity = intensity * (1 - progress)  # Decay over time

        offset_x = random.uniform(-current_intensity, current_intensity)
        offset_y = random.uniform(-current_intensity, current_intensity)

        camera.x = original_x + offset_x
        camera.y = original_y + offset_y

        display.flip()
        time.delay(10)

    # Reset to original position
    camera.x = original_x
    camera.y = original_y


def fade(fade_out: bool, screen: Surface, config, draw_callback=None, speed=3) -> None:
    """
    Fade to/from current scene to/from black.
    @param screen: The screen.
    @param config: The game configuration.
    @param draw_callback: Optional callback function to redraw game content (needed for fade_in).
    @param speed: Speed multiplier for fade effect (higher = faster). Default is 3.
    :return: None
    @type fade_out: bool
    If true, fades out. If false, fades in.
    """
    width, height = screen.get_width(), screen.get_height()
    fade_surface = Surface((width, height))  # lgtm [py/call/wrong-arguments]
    fade_surface.fill(BLACK)

    # For fade in, capture the current screen state
    if not fade_out:
        background = screen.copy()

    # Initialize opacity
    opacity = 0 if fade_out else 255

    # Adjust the range based on fade direction and speed
    alpha_range = range(0, 256, speed) if fade_out else range(255, -1, -speed)

    for alpha in alpha_range:
        # For fade in, restore the background before applying the fade
        if not fade_out:
            if draw_callback:
                draw_callback()
            else:
                screen.blit(background, (0, 0))

        fade_surface.set_alpha(opacity)
        screen.blit(fade_surface, (0, 0)) if not config['NO_BLIT'] else None
        display.update()
        if not config['NO_WAIT']:
            time.delay(5)

        # Update opacity based on fade direction
        if fade_out:
            opacity = min(255, opacity + speed)
        else:
            opacity = max(0, opacity - speed)


def draw_transparent_color(color, screen, transparency, no_blit):
    color_flash_surface = Surface((screen.get_width(), screen.get_height()))
    color_flash_surface.set_alpha(transparency)
    color_flash_surface.fill(color)
    if not no_blit:
        screen.blit(color_flash_surface, (0, 0))


def flash_transparent_color(color, screen, calculation, transparency=192, no_blit=False):
    start_time = get_ticks()
    draw_transparent_color(color, screen, transparency, no_blit)
    while calculation.convert_to_frames_since_start_time(start_time) < 3:
        display.flip()
