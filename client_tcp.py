import socket, sys, json, pygame

if len(sys.argv) != 3:
    print(f'Use: {sys.argv[0]} <ip_server> <port>')
    sys.exit(0)

ip = sys.argv[1]
port = int(sys.argv[2])

pygame.init()
cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
cliente.connect((ip, port))

init_data = json.loads(cliente.recv(1024).decode().strip())
CONFIG = init_data["config"]
side = init_data["side"]

#print(f'You are player {side[1]}')

BLUE_BG = (110, 193, 228)
BLACK = (0, 0, 0)
GOLD = (237, 187, 99)
WHITE = (255, 255, 255)

header_height = CONFIG["header_height"]
field_height = CONFIG["height"]
tela = pygame.display.set_mode((CONFIG["width"], field_height + header_height))
pygame.display.set_caption("Atari - Hockey (Client)")
relogio = pygame.time.Clock()

left_paddle_x = CONFIG["paddle"]["x_offset"]
right_paddle_x = CONFIG["width"] - left_paddle_x - CONFIG["paddle"]["w"]
left_vertical_x = CONFIG["goal"]["post_offset"]
right_vertical_x = CONFIG["width"] - left_vertical_x - CONFIG["goal"]["thickness"]
protrude = CONFIG["goal"]["protrude"]
post_thickness = CONFIG["goal"]["thickness"]
goal_center = field_height // 2
goal_half = CONFIG["goal"]["height"] // 2
goal_top = goal_center - goal_half
goal_bottom = goal_center + goal_half

def draw(state, remaining):
    tela.fill(BLUE_BG)
    pygame.draw.rect(tela, BLACK, (0, 0, CONFIG["width"], header_height), 3)
    font = pygame.font.Font(None, 80)
    score = state['score']
    left_score_text = font.render(str(score[0]), True, GOLD)
    tela.blit(left_score_text, (CONFIG["width"] // 6 - left_score_text.get_width() // 2, header_height // 2 - left_score_text.get_height() // 2))
    time_str = f"{int(remaining // 60):02}:{int(remaining % 60):02}"
    time_text = font.render(time_str, True, WHITE)
    tela.blit(time_text, (CONFIG["width"] // 2 - time_text.get_width() // 2, header_height // 2 - time_text.get_height() // 2))
    right_score_text = font.render(str(score[1]), True, GOLD)
    tela.blit(right_score_text, (3.3 * CONFIG["width"] // 4 - right_score_text.get_width() // 2, header_height // 2 - right_score_text.get_height() // 2))
    y_offset = header_height
    pygame.draw.circle(tela, BLACK, (int(state["ball"][0]), int(state["ball"][1]) + y_offset), CONFIG["ball"]["r"])
    pygame.draw.rect(tela, GOLD, (left_paddle_x, state["paddles"]["p1"] + y_offset, CONFIG["paddle"]["w"], CONFIG["paddle"]["h"]))
    pygame.draw.rect(tela, GOLD, (right_paddle_x, state["paddles"]["p2"] + y_offset, CONFIG["paddle"]["w"], CONFIG["paddle"]["h"]))
    pygame.draw.rect(tela, BLACK, (left_vertical_x, goal_top + y_offset, post_thickness, CONFIG["goal"]["height"]))
    pygame.draw.rect(tela, BLACK, (left_vertical_x, goal_top + y_offset, protrude, post_thickness))
    pygame.draw.rect(tela, BLACK, (left_vertical_x, goal_bottom + y_offset - post_thickness, protrude, post_thickness))
    pygame.draw.rect(tela, BLACK, (right_vertical_x, goal_top + y_offset, post_thickness, CONFIG["goal"]["height"]))
    pygame.draw.rect(tela, BLACK, (right_vertical_x - protrude + post_thickness, goal_top + y_offset, protrude, post_thickness))
    pygame.draw.rect(tela, BLACK, (right_vertical_x - protrude + post_thickness, goal_bottom + y_offset - post_thickness, protrude, post_thickness))
    pygame.display.flip()

running = True
game_over = False
command = "STOP"
remaining = CONFIG["game_duration"]
buffer = ""
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: 
            running = False
    
    if not game_over:
        keys = pygame.key.get_pressed()
        new_command = "UP" if keys[pygame.K_UP] else "DOWN" if keys[pygame.K_DOWN] else "STOP"
        if new_command != command:
            command = new_command
            cliente.sendall(command.encode())
        try:
            data_str = cliente.recv(1024).decode()
            if not data_str: break
            buffer += data_str
            while "\n" in buffer:
                message, buffer = buffer.split("\n", 1)
                if not message.strip(): continue
                data = json.loads(message)
                if data["status"] == "game_over":
                    tela.fill(BLUE_BG)
                    font = pygame.font.Font(None, 48)
                    winner = data["winner"]
                    score = data["score"]
                    if winner == "tie":
                        text = font.render(f"Tie! {score[0]} - {score[1]}", True, WHITE)
                    else:
                        winner_side = "You WIN!" if winner == side else "You LOSE!"
                        text = font.render(f"{winner_side} ({score[0]} - {score[1]})", True, WHITE)
                    tela.blit(text, text.get_rect(center=(CONFIG["width"] // 2, (field_height + header_height) // 2)))
                    pygame.display.flip()
                    cliente.close()
                    game_over = True
                else:
                    remaining = data["remaining"]
                    draw(data["state"], remaining)
        except (ConnectionResetError, json.JSONDecodeError): 
            break
    relogio.tick(60)

cliente.close()
pygame.quit()