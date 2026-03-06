import re
import math

# ==========================================
# 🎵 KTV 歌词转 ASS 配置文件 🎵
# ==========================================

# === 1. 文件路径 ===
INPUT_LRC = 'lyrics.lrc'
OUTPUT_ASS = 'output.ass'

# === 2. 视频与排版设置 ===
PLAY_RES_X = 1920
PLAY_RES_Y = 1080
MARGIN_L = 350  # 左侧边距（防止字幕贴边）
MARGIN_R = 350  # 右侧边距
MARGIN_V_L = 250  # 左侧主歌词高度（从底部起算）
MARGIN_V_R = 100  # 右侧主歌词高度（从底部起算）
MARGIN_V_TOP = 50  # 顶部括号和声高度（从顶部起算）

# === 3. 字体与字号设置 ===
FONT_NAME = '猫啃网糖圆体-测试版'  # 替换回你截图中使用的可爱字体
FONT_SIZE_MAIN = 90  # 主歌词字号
FONT_SIZE_TOP = 75  # 顶部和声字号
OUTLINE_WIDTH = 4  # 描边宽度
SHADOW_DEPTH = 3  # 阴影距离

# === 4. 颜色设置 ===
COLOR_PRIMARY = '&H00A86EFF'  # 唱过的颜色（亮绿/青色）
COLOR_SECONDARY = '&H00FFFFFF'  # 没唱的底色（纯白）
COLOR_OUTLINE = '&H00A0D873'  # 描边颜色（深绿）
COLOR_SHADOW = '&H80000000'  # 阴影颜色（半透明黑）

# === 5. 倒数圆点设置 ===
GAP_THRESHOLD = 5.0  # 间奏大于多少秒触发清屏与倒数
COUNTDOWN_TIME = 5.0  # 提前多少秒出现倒数点
DOT_CHAR = '●'  # 圆点字符
DOT_SIZE = 50  # 圆点字号（\fs50）
DOT_FADE_COLOR = COLOR_SECONDARY

# === 6. 智能断句设置 (核心优化区) ===
MAX_WIDTH_MAIN = 17  # 主歌词单行最大字数（全角）
MAX_WIDTH_TOP = 25  # 顶部和声单行最大字数

# 【动态断句阈值】当当前行字数达到最大长度的百分之多少时，允许在此处换行：
RATIO_PUNCT = 0.5  # 遇到真正的标点符号 (, . ? 等) -> 达到 50% 即可换行
RATIO_SPACE_CN = 0.6  # 遇到中英文交界处的空格 (如 "Spice 一不小心") -> 达到 60% 即可换行，保留完美语意
RATIO_SPACE_EN = 0.85  # 遇到纯英文之间的空格 (如 "Lock on") -> 必须达到 85% 极限才换行，防止拆散英文短语

# === 7. 时间轴微调 (延迟补偿) ===
GLOBAL_DELAY = 0.25


# ==========================================
# ⚙️ 核心转换逻辑（无需修改下方内容） ⚙️
# ==========================================

def get_inline_color(ass_color):
    clean = ass_color.replace('&H00', '&H', 1) if ass_color.startswith('&H00') else ass_color
    return clean + '&' if not clean.endswith('&') else clean


def convert_lrc_to_ass(lrc_file, ass_file):
    with open(lrc_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    style_format = "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"

    style_l = f"Style: L,{FONT_NAME},{FONT_SIZE_MAIN},{COLOR_PRIMARY},{COLOR_SECONDARY},{COLOR_OUTLINE},{COLOR_SHADOW},-1,0,0,0,100,100,0,0,1,{OUTLINE_WIDTH},{SHADOW_DEPTH},1,{MARGIN_L},{MARGIN_R},{MARGIN_V_L},1"
    style_r = f"Style: R,{FONT_NAME},{FONT_SIZE_MAIN},{COLOR_PRIMARY},{COLOR_SECONDARY},{COLOR_OUTLINE},{COLOR_SHADOW},-1,0,0,0,100,100,0,0,1,{OUTLINE_WIDTH},{SHADOW_DEPTH},3,{MARGIN_L},{MARGIN_R},{MARGIN_V_R},1"
    style_top = f"Style: Top,{FONT_NAME},{FONT_SIZE_TOP},{COLOR_PRIMARY},{COLOR_SECONDARY},{COLOR_OUTLINE},{COLOR_SHADOW},-1,0,0,0,100,100,0,0,1,{OUTLINE_WIDTH},{SHADOW_DEPTH},8,{MARGIN_L},{MARGIN_R},{MARGIN_V_TOP},1"

    ass_lines = [
        "[Script Info]",
        "Title: Karaoke Lyrics (Smart Break)",
        "ScriptType: v4.00+",
        f"PlayResX: {PLAY_RES_X}",
        f"PlayResY: {PLAY_RES_Y}",
        "",
        "[V4+ Styles]",
        style_format,
        style_l,
        style_r,
        style_top,
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    def format_ass_time(seconds):
        delta = int(round(seconds * 100))
        h = delta // 360000
        m = (delta % 360000) // 6000
        s = (delta % 6000) // 100
        cs = delta % 100
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def get_word_width(text):
        return sum(1 if '\u4e00' <= c <= '\u9fff' else 0.5 for c in text)

    pattern = re.compile(r'\[(\d{2}):(\d{2}\.\d{2,3})\]([^\[]*)')

    parsed_lines_main = []
    parsed_lines_top = []

    def process_words(words_list, max_width):
        if not words_list: return []
        total_width = sum(get_word_width(w[0]) for w in words_list)
        if total_width <= max_width: return [words_list]

        local_chunks = []
        current_chunk = []
        current_width = 0

        for i, w in enumerate(words_list):
            w_text = w[0]
            w_width = get_word_width(w_text)
            current_chunk.append(w)
            current_width += w_width

            if i == len(words_list) - 1: break

            next_w_text = words_list[i + 1][0]
            next_w_width = get_word_width(next_w_text)

            # 1. 强制断句：如果加上下一个字就爆表了，必须立刻换行
            if current_width + next_w_width > max_width:
                local_chunks.append(current_chunk)
                current_chunk = []
                current_width = 0
                continue

            # 2. 动态智能断句分析
            has_strong_punct = bool(re.search(r'[\.,\?!\;:"\'，。？！、；：“”‘’]', w_text))
            has_space = ' ' in w_text or '　' in w_text

            is_curr_chinese = bool(re.search(r'[\u4e00-\u9fff]', w_text))
            is_next_chinese = bool(re.search(r'[\u4e00-\u9fff]', next_w_text))

            threshold_ratio = 1.1  # 默认值 > 1，代表在不满足条件时绝不提前断句

            if has_strong_punct:
                threshold_ratio = RATIO_PUNCT
            elif has_space:
                # 判断空格的性质：是否有中文字符参与
                if is_curr_chinese or is_next_chinese:
                    threshold_ratio = RATIO_SPACE_CN  # 中英/中中交界处，容易断开
                else:
                    threshold_ratio = RATIO_SPACE_EN  # 纯英文之间的空格，极难断开

            # 只有当当前累计长度达到了我们判定的阈值，才执行优雅的提前换行
            if current_width >= max_width * threshold_ratio:
                local_chunks.append(current_chunk)
                current_chunk = []
                current_width = 0

        if current_chunk: local_chunks.append(current_chunk)
        return local_chunks

    for line in lines:
        matches = pattern.findall(line)
        if not matches: continue

        tokens = []
        for m in matches:
            time_sec = int(m[0]) * 60 + float(m[1]) + GLOBAL_DELAY
            time_sec = max(0.0, time_sec)
            tokens.append((time_sec, m[2]))

        words = []

        for j in range(len(tokens) - 1):
            start_t = tokens[j][0]
            text = tokens[j][1]
            end_t = tokens[j + 1][0]
            if text: words.append((text, start_t, end_t))

        last_t, last_text = tokens[-1]
        last_text = last_text.replace('\n', '')
        if last_text: words.append((last_text, last_t, last_t + len(last_text) * 0.3))

        if words:
            main_words, paren_words = [], []
            in_paren = False

            for text, start_t, end_t in words:
                if '(' in text or '（' in text: in_paren = True
                clean_text = re.sub(r'[()（）]', '', text)
                if in_paren:
                    if clean_text: paren_words.append((clean_text, start_t, end_t))
                else:
                    if clean_text: main_words.append((clean_text, start_t, end_t))
                if ')' in text or '）' in text: in_paren = False

            for chunk in process_words(main_words, MAX_WIDTH_MAIN):
                parsed_lines_main.append({
                    'words': [(w[0], max(0, int(round((w[2] - w[1]) * 100)))) for w in chunk],
                    'sing_start': chunk[0][1],
                    'sing_end': chunk[-1][2],
                    'type': 'main'
                })

            for chunk in process_words(paren_words, MAX_WIDTH_TOP):
                parsed_lines_top.append({
                    'words': [(w[0], max(0, int(round((w[2] - w[1]) * 100)))) for w in chunk],
                    'sing_start': chunk[0][1],
                    'sing_end': chunk[-1][2],
                    'type': 'top'
                })

    last_end_L = 0.0
    last_end_R = 0.0
    current_style = 'R'

    for i, data in enumerate(parsed_lines_main):
        gap = data['sing_start'] if i == 0 else data['sing_start'] - parsed_lines_main[i - 1]['sing_end']
        data['disp_end'] = data['sing_end'] + 0.5

        if gap > GAP_THRESHOLD:
            current_style = 'L'
            clear_time = max(data['sing_start'] - COUNTDOWN_TIME, last_end_L, last_end_R)
            data['style'] = current_style
            data['disp_start'] = clear_time
            data['needs_countdown'] = True
            last_end_L = data['disp_end']
            last_end_R = clear_time
        else:
            current_style = 'R' if current_style == 'L' else 'L'
            data['style'] = current_style
            data['needs_countdown'] = False
            if current_style == 'L':
                data['disp_start'] = last_end_L
                last_end_L = data['disp_end']
            else:
                data['disp_start'] = last_end_R
                last_end_R = data['disp_end']

        if data['disp_start'] >= data['disp_end']:
            data['disp_start'] = data['disp_end'] - 0.1

    countdown_events = []
    for data in parsed_lines_main:
        if data.get('needs_countdown'):
            margin_v = MARGIN_V_L + 100 if data['style'] == 'L' else MARGIN_V_R + 100
            countdown_events.append({
                'type': 'countdown',
                'disp_start': data['disp_start'],
                'disp_end': data['sing_start'],
                'style': data['style'],
                'margin_v': margin_v,
                'sing_start': data['sing_start']
            })

    for i, data in enumerate(parsed_lines_top):
        data['style'] = 'Top'
        data['disp_end'] = data['sing_end'] + 0.5
        data['disp_start'] = max(0, data['sing_start'] - 1.0)
        if i >= 1:
            prev_end = parsed_lines_top[i - 1]['disp_end']
            if data['disp_start'] < prev_end: data['disp_start'] = prev_end
        if data['disp_start'] >= data['disp_end']: data['disp_start'] = data['disp_end'] - 0.1

    all_lines = parsed_lines_main + parsed_lines_top + countdown_events
    all_lines.sort(key=lambda x: x['disp_start'])

    active_c = f"\\1c{get_inline_color(COLOR_PRIMARY)}"
    inactive_c = f"\\c{get_inline_color(DOT_FADE_COLOR)}"

    for data in all_lines:
        ass_start = format_ass_time(data['disp_start'])
        ass_end = format_ass_time(data['disp_end'])

        if data.get('type') == 'countdown':
            margin_v = data['margin_v']
            dots_list = [
                f"{{f\\s{DOT_SIZE}{active_c}\\t(4100,4900,{inactive_c})}}{DOT_CHAR}",
                f"{{{active_c}\\t(3100,3900,{inactive_c})}}{DOT_CHAR}",
                f"{{{active_c}\\t(2100,2900,{inactive_c})}}{DOT_CHAR}",
                f"{{{active_c}\\t(1100,1900,{inactive_c})}}{DOT_CHAR}",
                f"{{{active_c}\\t(100,900,{inactive_c})}}{DOT_CHAR}"
            ]
            retreating_dots = " ".join(dots_list)
            ass_lines.append(
                f"Dialogue: 0,{ass_start},{ass_end},{data['style']},,0,0,{margin_v},,{{\\fad(200,0)}}{retreating_dots}")
        else:
            preroll_cs = max(0, int(round((data['sing_start'] - data['disp_start']) * 100)))
            k_text = f"{{\\fad(200,200)\\k{preroll_cs}}}"
            for text, dur_cs in data['words']:
                k_text += f"{{\\kf{dur_cs}}}{text}"
            ass_lines.append(f"Dialogue: 0,{ass_start},{ass_end},{data['style']},,0,0,0,,{k_text}")

    with open(ass_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(ass_lines))

    print(f"✅ 转换成功！已生成 {ass_file} (应用延迟: {GLOBAL_DELAY}秒)")


if __name__ == '__main__':
    convert_lrc_to_ass(INPUT_LRC, OUTPUT_ASS)