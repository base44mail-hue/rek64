import os
import sys
import random
import time

# ==== C64 HEADER TEXT ====
C64_HEADER = """
**** COMMODORE 64 BASIC V2 ****
64K RAM SYSTEM  38911 BASIC BYTES FREE
READY.
"""

# ==== FULLSCREEN-FUNKTION ====
def go_true_fullscreen():
    if os.name == "nt":
        try:
            import ctypes
            user32 = ctypes.WinDLL("user32")
            VK_F11 = 0x7A
            KEYEVENTF_EXTENDEDKEY = 0x1

            # Press F11
            user32.keybd_event(VK_F11, 0, KEYEVENTF_EXTENDEDKEY, 0)
            time.sleep(0.05)
            # Release F11
            user32.keybd_event(VK_F11, 0, KEYEVENTF_EXTENDEDKEY | 0x2, 0)

        except Exception as e:
            print("Fullscreen error:", e)

    os.system("cls" if os.name == "nt" else "clear")

# ==== MENÜ ====
def show_menu():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=== REK-C64 OS MENU ===")
    print("1) START BASIC")
    print("2) ABOUT")
    print("3) EXIT")

    while True:
        choice = input("\nSelect [1-3]: ").strip()
        if choice == "1":
            return "start"
        elif choice == "2":
            print("\nREK-C64 OS")
            print("Clean startup with fullscreen BASIC.")
            print("Created for Sebastian.\n")
            input("Press ENTER to return to menu...")
            return show_menu()
        elif choice == "3":
            print("\nBYE.")
            sys.exit(0)
        else:
            print("?SYNTAX ERROR")

# ==== BASIC ENGINE ====
program = {}
variables = {}
for_stack = []
gosub_stack = []
ram = [0]*65536

def c64_print(text):
    print(str(text)[:26])

def eval_expr(expr):
    expr = expr.upper()
    for var in variables:
        expr = expr.replace(var.upper(), str(variables[var]))
    expr = expr.replace("RND", str(random.random()))
    try:
        return eval(expr)
    except:
        return 0

def eval_string(func, args):
    args = args.strip()
    if func == "CHR$":
        return chr(int(eval_expr(args)))
    if func == "LEFT$":
        s,n = args.split(",")
        s = s.strip('"')
        return s[:int(eval_expr(n))]
    if func == "RIGHT$":
        s,n = args.split(",")
        s = s.strip('"')
        return s[-int(eval_expr(n)):]
    if func == "MID$":
        s,start,length = args.split(",")
        s = s.strip('"')
        return s[int(eval_expr(start))-1:int(eval_expr(start))-1+int(eval_expr(length))]
    if func == "STR$":
        return str(eval_expr(args))
    if func == "VAL":
        return float(args)
    if func == "LEN":
        return len(args.strip('"'))
    if func == "ASC":
        return ord(args.strip('"')[0])

def run_program():
    global program, variables, for_stack, gosub_stack
    keys = sorted(program.keys())
    pointer = 0
    while pointer < len(keys):
        line_num = keys[pointer]
        line = program[line_num].strip()
        line_upper = line.upper()
        if line_upper.startswith("REM") or line == "":
            pointer += 1
            continue
        if line_upper in ("END", "STOP"):
            break

        # LET
        if line_upper.startswith("LET"):
            try:
                var, val = line[3:].split("=")
                variables[var.strip()] = eval_expr(val)
            except:
                pass
            pointer += 1
            continue

        # PRINT
        elif line_upper.startswith("PRINT"):
            content = line[5:].strip()
            fcts = ["CHR$", "LEFT$", "RIGHT$", "MID$", "STR$", "VAL", "LEN", "ASC"]
            if any(content.upper().startswith(f) for f in fcts):
                for f in fcts:
                    if content.upper().startswith(f):
                        inner = content[len(f):].strip("()")
                        c64_print(eval_string(f, inner))
                        break
            elif '"' in content:
                c64_print(content.replace('"', ''))
            else:
                c64_print(eval_expr(content))
            pointer += 1
            continue

        # INPUT
        elif line_upper.startswith("INPUT"):
            var = line[5:].strip()
            val = input("? ")
            if var.endswith("$"):
                variables[var] = val
            else:
                try:
                    variables[var] = float(val)
                except:
                    variables[var] = 0
            pointer += 1
            continue

        # IF THEN
        elif line_upper.startswith("IF") and "THEN" in line_upper:
            cond, cmd = line.split("THEN", 1)
            cond = cond[2:].strip()
            if eval_expr(cond):
                if cmd.upper().startswith("PRINT"):
                    c64_print(cmd[5:].replace('"', ''))
                elif cmd.upper().startswith("LET"):
                    try:
                        var, val = cmd[3:].split("=")
                        variables[var.strip()] = eval_expr(val)
                    except:
                        pass
                elif cmd.upper().startswith("GOTO"):
                    target = int(cmd[4:].strip())
                    if target in program:
                        pointer = sorted(program.keys()).index(target)
                        continue
            pointer += 1
            continue

        # GOTO
        elif line_upper.startswith("GOTO"):
            target = int(line[4:].strip())
            if target in program:
                pointer = sorted(program.keys()).index(target)
                continue

        # GOSUB / RETURN
        elif line_upper.startswith("GOSUB"):
            target = int(line[5:].strip())
            gosub_stack.append(pointer + 1)
            if target in program:
                pointer = sorted(program.keys()).index(target)
                continue
        elif line_upper == "RETURN":
            if gosub_stack:
                pointer = gosub_stack.pop()
                continue
            pointer += 1
            continue

        # FOR / NEXT
        elif line_upper.startswith("FOR"):
            try:
                parts = line[3:].split("=")
                var = parts[0].strip()
                rest = parts[1].strip()
                step = 1
                if "STEP" in rest.upper():
                    to_idx = rest.upper().find("TO")
                    step_idx = rest.upper().find("STEP")
                    start = eval_expr(rest[:to_idx])
                    end = eval_expr(rest[to_idx + 2:step_idx])
                    step = eval_expr(rest[step_idx + 4:])
                else:
                    to_idx = rest.upper().find("TO")
                    start = eval_expr(rest[:to_idx])
                    end = eval_expr(rest[to_idx + 2:])
                variables[var] = start
                for_stack.append({"var": var, "end": end, "step": step, "line": pointer})
            except:
                pass
            pointer += 1
            continue
        elif line_upper.startswith("NEXT"):
            var = line[4:].strip()
            if for_stack:
                top = for_stack[-1]
                top_var = top["var"] if var == "" else var
                variables[top_var] += top["step"]
                if (top["step"] > 0 and variables[top_var] <= top["end"]) or (top["step"] < 0 and variables[top_var] >= top["end"]):
                    pointer = top["line"]
                    continue
                else:
                    for_stack.pop()
            pointer += 1
            continue

        # POKE / PEEK
        elif line_upper.startswith("POKE"):
            try:
                addr, val = line[4:].split(",")
                ram[int(eval_expr(addr))] = int(eval_expr(val))
            except:
                pass
            pointer += 1
            continue
        elif "PEEK" in line_upper:
            start = line_upper.find("PEEK(") + 5
            end = line_upper.find(")", start)
            addr = line_upper[start:end]
            c64_print(ram[int(eval_expr(addr))])
            pointer += 1
            continue

        pointer += 1

def basic_main():
    go_true_fullscreen()  # Direkt Vollbild beim Start von BASIC
    print(C64_HEADER)
    while True:
        cmd = input("> ").upper().strip()
        if cmd == "":
            print("READY.")
            continue
        if cmd == "LIST":
            for num in sorted(program.keys()):
                c64_print(f"{num} {program[num]}")
            continue
        if cmd == "RUN":
            run_program()
            continue
        if cmd == "NEW":
            program.clear()
            variables.clear()
            for_stack.clear()
            gosub_stack.clear()
            print("READY.")
            continue
        if cmd == "MENU":
            return
        if cmd == "EXIT":
            sys.exit(0)
        if cmd[0].isdigit():
            if " " in cmd:
                num, line = cmd.split(" ", 1)
                program[int(num)] = line
            else:
                program[int(cmd)] = ""
            continue
        print("READY.")

# ==== BOOT ====
def main():
    choice = show_menu()
    if choice == "start":
        basic_main()

if __name__ == "__main__":
    main()
