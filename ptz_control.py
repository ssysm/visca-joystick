import pygame
import json
import sys
import os 
import time

from visca_over_ip.exceptions import ViscaException
from numpy import interp

from visca_over_ip import Camera

os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

sensitivity_tables = {
    'pan': {'joy': [0, 0.05, 0.3, 0.7, 0.9, 1], 'cam': [0, 0, 2, 8, 15, 20]},
    'tilt': {'joy': [0, 0.07, 0.3, 0.65, 0.85, 1], 'cam': [0, 0, 3, 6, 14, 18]},
    'zoom': {'joy': [0, 0.1, 1], 'cam': [0, 0, 7]},
}

def joy_pos_to_cam_speed(axis_position: float, table_name: str, invert=True) -> int:
    """Converts from a joystick axis position to a camera speed using the given mapping

    :param axis_position: the raw value of an axis of the joystick -1 to 1
    :param table_name: one of the keys in sensitivity_tables
    :param invert: if True, the sign of the output will be flipped
    :return: an integer which can be fed to a Camera driver method
    """
    sign = 1 if axis_position >= 0 else -1
    if invert:
        sign *= -1

    table = sensitivity_tables[table_name]

    return sign * round(
        interp(abs(axis_position), table['joy'], table['cam'])
    )

def connect_to_camera(ip: str, port: int) -> Camera:
    """Connects to the camera specified by cam_index and returns it"""
    camera = Camera(ip, port)

    try:
        camera.zoom(0)
    except ViscaException:
        pass

    return camera

# Function to load configuration
def load_config(file_path='config.json'):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# # Function to initialize Pygame and joystick
# def init_pygame():
#     pygame.init()
#     pygame.joystick.init()
#     joystick = pygame.joystick.Joystick(0)
#     joystick.init()
#     return joystick

# Function to display camera status on screen
def display_status(screen, font, focus_mode, zoom_level, pan_speed, tilt_speed):
    screen.fill((0, 0, 0))  # Clear screen
    focus_text = font.render(f"Focus Mode: {focus_mode}", True, (255, 255, 255))
    zoom_text = font.render(f"Zoom Level: {zoom_level}", True, (255, 255, 255))
    pt_speed_text = font.render(f"Pan Speed: {pan_speed}, Tilt Speed: {tilt_speed}", True, (255, 255, 255))

    # Render text to screen
    screen.blit(focus_text, (20, 20))
    screen.blit(zoom_text, (20, 70))
    screen.blit(pt_speed_text, (20, 120))
    pygame.display.flip()  # Update display

def main_loop(config, camera: Camera):
    controller_mapping = load_config(config['controller_mapping'])
    # Initialize Pygame
    pygame.init()
    screen = pygame.display.set_mode((500, 300))
    pygame.display.set_caption("PTZ Camera Control")
    font = pygame.font.Font(None, 36)

    # Used to manage how fast the screen updates.
    clock = pygame.time.Clock()

    # Camera status variables
    focus_mode = "Auto"
    invert_tilt = controller_mapping['invert_tilt']
    invert_pan = controller_mapping['invert_pan']
    invert_zoom = controller_mapping['invert_zoom']
    
    pan_speed = 0
    old_pan_speed = 0
    tilt_speed = 0
    old_tilt_speed = 0
    
    zoom_level = 0
    joysticks = {}

    # Main loop
    running = True
    # pygame.event.set_grab(True) # Keeps the cursor within the pygame window
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.JOYBUTTONDOWN:
                # Toggle focus mode
                if event.button == controller_mapping['focus_toggle_button']:
                    # toggle_focus()
                    focus_mode = "Manual" if focus_mode == "Auto" else "Auto"
            # Handle hotplugging
            if event.type == pygame.JOYDEVICEADDED:
                # This event will be generated when the program starts for every
                # joystick, filling up the list without needing to create them manually.
                joy = pygame.joystick.Joystick(event.device_index)
                joysticks[joy.get_instance_id()] = joy
                print(f"Joystick {joy.get_instance_id()} connencted")

            if event.type == pygame.JOYDEVICEREMOVED:
                del joysticks[event.instance_id]
                print(f"Joystick {event.instance_id} disconnected")
        if  len(joysticks) == 0:
            continue
        # use the first joystick
        joystick = joysticks[list(joysticks.keys())[0]]

        for axis in range(joystick.get_numaxes()):
            axis_position = joystick.get_axis(axis)
            if axis == controller_mapping['pan_axis']:
                pan_speed = joy_pos_to_cam_speed(axis_position, 'pan', invert=invert_pan)
            elif axis == controller_mapping['tilt_axis']:
                tilt_speed = joy_pos_to_cam_speed(axis_position, 'tilt', invert=invert_tilt)
            elif axis == controller_mapping['zoom_axis']:
                zoom_level = joy_pos_to_cam_speed(axis_position, 'zoom', invert=invert_zoom)
                camera.zoom(zoom_level)
        if pan_speed != old_pan_speed or tilt_speed != old_tilt_speed:
            camera.pantilt(pan_speed, tilt_speed)
        # Display camera status
        display_status(screen, font, focus_mode, zoom_level, pan_speed, tilt_speed)
        
        old_pan_speed = pan_speed
        old_tilt_speed = tilt_speed
        clock.tick(200)

    # Cleanup
    pygame.quit()
    sys.exit()

def configure():
    # Load configuration
    config = load_config()

    return {
        'camera_ip': config['camera']['ip'],
        'camera_port': config['camera']['port'],
        'controller_mapping': config['controller_mapping'],
    }


if __name__ == "__main__":
    print('Welcome to VISCA Joystick!')

    while True:
        try:
            config_dict = configure()
            cam = connect_to_camera(config_dict['camera_ip'], config_dict['camera_port'])
            main_loop(config_dict, cam)
            break
        except Exception as exc:
            print(exc)
            print('Initialization error. Check that all network equipment is connected and powered on.')
            input('Press enter to retry: ')
