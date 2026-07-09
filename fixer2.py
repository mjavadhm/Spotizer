import codecs

# === MESSAGE ROUTES ===
with codecs.open('bale_bot/routes/message_routes.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_wrapper = False
passed_wrapper = False

for line in lines:
    if line.startswith('def setup_message_routes'):
        in_wrapper = True
        new_lines.append('download_controller = BaleDownloadController()\n')
        new_lines.append('playlist_controller = BalePlaylistController()\n')
        new_lines.append('url_validator = URLValidator()\n')
        continue
        
    if in_wrapper:
        if '"""' in line: continue
        if line.startswith('    url_validator ='): continue
        if line.startswith('    playlist_controller ='): continue
        if line.startswith('    logger.info('):
            new_lines.append('logger.info("Setting up message routes for Bale")\n')
            in_wrapper = False
            passed_wrapper = True
            continue

    if passed_wrapper and line.startswith('    '):
        new_lines.append(line[4:])
    elif passed_wrapper and line == '\n':
        new_lines.append(line)
    else:
        new_lines.append(line)

# Fix arguments
for i, line in enumerate(new_lines):
    if line.startswith('async def ') and '(message):' in line:
        new_lines[i] = line.replace('(message):', '(*, message):')
    if line.startswith('async def handle_music_link(message, url: str, download_controller'):
        new_lines[i] = line.replace('message, url: str, download_controller', '*, message, url: str')
    if line.startswith('async def handle_search_query(message, query: str):'):
        new_lines[i] = line.replace('message, query: str', '*, message, query: str')

with codecs.open('bale_bot/routes/message_routes.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)


# === CALLBACK ROUTES ===
with codecs.open('bale_bot/routes/callback_routes.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_wrapper = False
passed_wrapper = False

for line in lines:
    if line.startswith('def setup_callback_routes'):
        in_wrapper = True
        new_lines.append('user_controller = BaleUserController()\n')
        new_lines.append('download_controller = BaleDownloadController()\n')
        new_lines.append('playlist_controller = BalePlaylistController()\n')
        continue
        
    if in_wrapper:
        if '"""' in line: continue
        if line.startswith('    logger.info('):
            new_lines.append('logger.info("Setting up callback routes for Bale")\n')
            in_wrapper = False
            passed_wrapper = True
            continue

    if passed_wrapper and line.startswith('    '):
        new_lines.append(line[4:])
    elif passed_wrapper and line == '\n':
        new_lines.append(line)
    else:
        new_lines.append(line)

# Fix arguments
for i, line in enumerate(new_lines):
    if line.startswith('async def ') and '(callback_query):' in line:
        new_lines[i] = line.replace('(callback_query):', '(*, callback_query):')

with codecs.open('bale_bot/routes/callback_routes.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

