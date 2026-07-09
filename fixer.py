import codecs

with codecs.open('bale_bot/routes/command_routes.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_wrapper = False
for line in lines:
    if line.startswith('def setup_command_routes'):
        in_wrapper = True
        new_lines.append('user_controller = BaleUserController()\n')
        new_lines.append('playlist_controller = BalePlaylistController()\n')
        continue
        
    if in_wrapper:
        if line.strip() == '\"\"\"Set up command route handlers for Bale bot\"\"\"':
            continue
        if line.startswith('    logger.info('):
            new_lines.append('logger.info("Setting up command routes for Bale")\n')
            in_wrapper = False
            continue

    if line.startswith('    @bot.on_') or line.startswith('    async def ') or line.startswith('    logger.info("Command routes setup'):
        new_lines.append(line[4:])
    elif line.startswith('    '):
        new_lines.append(line[4:])
    else:
        new_lines.append(line)

# Replace start_command arguments
for i, line in enumerate(new_lines):
    if line.startswith('async def ') and '(message):' in line:
        new_lines[i] = line.replace('(message):', '(*, message):')

with codecs.open('bale_bot/routes/command_routes.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
