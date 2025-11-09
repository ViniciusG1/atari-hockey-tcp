import socket, sys, json, time, threading, random

if len(sys.argv) != 2:
    print(f'Use: {sys.argv[0]} <port>')
    sys.exit(0)
    
ip = 'localhost'
port = int(sys.argv[1])

CONFIG = {
    "width": 800, "height": 400,
    "header_height": 100,
    "game_duration": 180,  # 3 * 60
    "paddle": {"w": 14, "h": 30, "speed": 5, "x_offset": 100},
    "ball": {"r": 6, "speed": 5},
    "goal": {"height": 150, "post_offset": 50, "protrude": 46, "thickness": 14}
}

def reset_game_state():
    return {
        "ball": [CONFIG["width"] // 2, CONFIG["height"] // 2],
        "vel": [CONFIG["ball"]["speed"], CONFIG["ball"]["speed"] * 0.5],
        "paddles": {
            "p1": CONFIG["height"] // 2 - CONFIG["paddle"]["h"] // 2, # left player
            "p2": CONFIG["height"] // 2 - CONFIG["paddle"]["h"] // 2  # right player
        },
        "score": [0, 0]
    }

state = reset_game_state()
cmds = {"p1": "STOP", "p2": "STOP"}
clients = []
game_active = False

goal_center = CONFIG["height"] // 2
goal_half = CONFIG["goal"]["height"] // 2
goal_top = goal_center - goal_half
goal_bottom = goal_center + goal_half

left_back = {'x': CONFIG["goal"]["post_offset"], 'y': goal_top, 'w': CONFIG["goal"]["thickness"], 'h': CONFIG["goal"]["height"]}
left_top = {'x': CONFIG["goal"]["post_offset"], 'y': goal_top, 'w': CONFIG["goal"]["protrude"], 'h': CONFIG["goal"]["thickness"]}
left_bottom = {'x': CONFIG["goal"]["post_offset"], 'y': goal_bottom - CONFIG["goal"]["thickness"], 'w': CONFIG["goal"]["protrude"], 'h': CONFIG["goal"]["thickness"]}

right_back = {'x': CONFIG["width"] - CONFIG["goal"]["post_offset"] - CONFIG["goal"]["thickness"], 'y': goal_top, 'w': CONFIG["goal"]["thickness"], 'h': CONFIG["goal"]["height"]}
right_top = {'x': CONFIG["width"] - CONFIG["goal"]["post_offset"] - CONFIG["goal"]["protrude"], 'y': goal_top, 'w': CONFIG["goal"]["protrude"], 'h': CONFIG["goal"]["thickness"]}
right_bottom = {'x': CONFIG["width"] - CONFIG["goal"]["post_offset"] - CONFIG["goal"]["protrude"], 'y': goal_bottom - CONFIG["goal"]["thickness"], 'w': CONFIG["goal"]["protrude"], 'h': CONFIG["goal"]["thickness"]}

sides = [left_top, left_bottom, right_top, right_bottom, left_back, right_back]
backs = [(left_back, 1, -1), (right_back, 0, 1)]  # (rect, score_index, reset_direction)

def clamp(v, a, b):
    return max(a, min(b, v))

def reset_ball(direction=1):
    state["ball"] = [CONFIG["width"] // 2, CONFIG["height"] // 2]
    state["vel"] = [CONFIG["ball"]["speed"] * direction, CONFIG["ball"]["speed"] * 0.5 * random.choice([-1, 1])]

def check_collision(rect, bx, by, r, vx, vy):
    rx, ry, rw, rh = rect['x'], rect['y'], rect['w'], rect['h']
    testx = clamp(bx, rx, rx + rw)
    testy = clamp(by, ry, ry + rh)
    dx = bx - testx
    dy = by - testy
    if (dx**2 + dy**2)**0.5 > r:
        return bx, by, vx, vy, False
    scored = False
    if dx != 0:
        vx = -vx
        bx += 2 * dx
    if dy != 0:
        vy = -vy
        by += 2 * dy
    return bx, by, vx, vy, scored

def update_game():
    bx, by = state["ball"]
    vx, vy = state["vel"]
    bx += vx
    by += vy
    r = CONFIG["ball"]["r"]
    if by - r < 0:
        by = r
        vy = -vy
    elif by + r > CONFIG["height"]:
        by = CONFIG["height"] - r
        vy = -vy

    for side in ("p1", "p2"):
        if cmds[side] == "UP":
            state["paddles"][side] -= CONFIG["paddle"]["speed"]
        elif cmds[side] == "DOWN":
            state["paddles"][side] += CONFIG["paddle"]["speed"]
        state["paddles"][side] = clamp(state["paddles"][side], 0, CONFIG["height"] - CONFIG["paddle"]["h"])

    left_y = state["paddles"]["p1"]
    right_y = state["paddles"]["p2"]
    left_paddle_right = CONFIG["paddle"]["x_offset"] + CONFIG["paddle"]["w"]
    right_paddle_left = CONFIG["width"] - CONFIG["paddle"]["x_offset"] - 10

    adjustment_paddle = 5 # ajuste na colisão vertial dos paddles
    if vx < 0 and bx - r <= left_paddle_right and left_y - adjustment_paddle <= by <= left_y + CONFIG["paddle"]["h"] + adjustment_paddle:
        vx = abs(vx)
    elif vx > 0 and bx + r >= right_paddle_left and right_y - adjustment_paddle <= by <= right_y + CONFIG["paddle"]["h"] + adjustment_paddle:
        vx = -abs(vx)

    for rect in sides:
        bx, by, vx, vy, _ = check_collision(rect, bx, by, r, vx, vy)
    
    offset = 4  # Deslocamento fixo para dentro do gol
    for back, score_idx, reset_dir in backs:
        if score_idx == 1:  # Gol esquerdo
            coll_x = back['x'] + offset
        else:  # Gol direito  
            coll_x = back['x'] - offset
            
        rx, ry, rw, rh = coll_x, back['y'], back['w'], back['h']
        testx = clamp(bx, rx, rx + rw)
        testy = clamp(by, ry, ry + rh)
        dist = (bx - testx)**2 + (by - testy)**2
        if dist**0.5 <= r:
            state["score"][score_idx] += 1
            reset_ball(reset_dir)
            return

    if bx - r <= 0:
        bx = r
        vx = -vx
    if bx + r >= CONFIG["width"]:
        bx = CONFIG["width"] - r
        vx = -vx

    state["vel"] = [vx, vy]
    state["ball"] = [bx, by]

def client_thread(conn, side):
    global game_active
    try:
        conn.sendall(json.dumps({"config": CONFIG, "side": side}).encode() + b"\n")
        while game_active:
            try:
                data = conn.recv(1024).decode().strip().upper()
                if not data: 
                    break
                if data in ("UP", "DOWN", "STOP"):
                    cmds[side] = data
            except: 
                break
    except:
        pass
    # Se um cliente desconectar, encerra o jogo
    game_active = False
    conn.close()

def main():
    global state, cmds, clients, game_active
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((ip, port))
        s.listen(2)

        while True:
            print("Waiting players...")
            
            # Reseta o estado do jogo
            state = reset_game_state()
            cmds = {"p1": "STOP", "p2": "STOP"}
            clients = []
            game_active = True
            
            for side in ("p1", "p2"):
                conn, addr = s.accept()
                clients.append(conn)
                threading.Thread(target=client_thread, args=(conn, side), daemon=True).start()
            
            print("Game Start!")    
            reset_ball()
            start_time = time.time()
            
            while game_active:
                # Verifica o tempo, time.time(), uso de syscall, porém, mantém precisão do tempo...
                remaining = max(0, CONFIG["game_duration"] - (time.time() - start_time)) 
                if remaining <= 0:
                    left_score, right_score = state["score"]
                    winner = "p1" if left_score > right_score else "p2" if right_score > left_score else "tie"
                    final_data = json.dumps({"status": "game_over", "winner": winner, "score": state["score"]}).encode() + b"\n"
                    for conn in clients:
                        try:
                            conn.sendall(final_data)
                        except: 
                            pass
                    break
                
                update_game()
                data = json.dumps({"status": "playing", "state": state, "remaining": remaining}).encode() + b"\n"
                
                disconnected = False
                for conn in clients:
                    try: 
                        conn.sendall(data)
                    except: 
                        disconnected = True
                
                if disconnected:
                    game_active = False
                    break
                    
                time.sleep(1/60)
            
            for conn in clients:
                try:
                    conn.close()
                except:
                    pass
            
            print("Game over. Waiting for next players...\n")

if __name__ == "__main__":
    main()