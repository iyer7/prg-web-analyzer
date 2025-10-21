import matplotlib

matplotlib.use('Agg')  # Use a non-interactive backend for the server
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import re
import numpy as np
import os
import math
import configparser


# --- CONFIGURATION (No changes) ---
def get_config_path():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.getcwd()
    return os.path.join(script_dir, 'analyzer_config.ini')


# --- PARSER (No changes, just removed tkinter popups) ---
def parse_prg_file(filename):
    feature_map = []
    try:
        with open(filename, 'r') as file:
            for i, line in enumerate(file, 1):
                if line.strip().startswith("!Feature"):
                    try:
                        num = int(line.strip().split(" ")[1])
                        feature_map.append({'end_line': i, 'number': num})
                    except (IndexError, ValueError):
                        pass
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found during parsing: {filename}")
    except Exception as e:
        raise Exception(f"Could not read the file. Error: {e}")

    feature_map.sort(key=lambda f: f['end_line'])

    # ... (Rest of the parse_prg_file function is identical, so it is omitted for brevity) ...

    def get_feature_for_line(line_num):
        """Given a line number, find which feature it belongs to."""
        for feature in feature_map:
            if line_num <= feature['end_line']:
                return feature['number']
        return feature_map[-1]['number'] if feature_map else 1

    all_segments = []
    is_printing = False
    last_x, last_y = None, None
    ptp_ev_pattern = re.compile(r"PTP/ev\s*\((X,Y)\),([-.\d]+),([-.\d]+),(.+)")
    ptp_e_pattern = re.compile(r"PTP/e\s*\((X,Y)\),([-.\d]+),([-.\d]+)")
    mseg_command_pattern = re.compile(r"MSEG(?:/v)?\s*\((X,Y)\),([-.\d]+),([-.\d]+)")
    mseg_line_pattern = re.compile(r"LINE\s*\((X,Y)\),([-.\d]+),([-.\d]+)")
    mseg_arc2_pattern = re.compile(r"ARC2\s*\((X,Y)\),([-.\d]+),([-.\d]+),([-.\d]+)")
    with open(filename, 'r') as file:
        lines = file.readlines()
    for line_num, line_content in enumerate(lines, 1):
        line = line_content.strip()
        if not line or line.startswith("!"):
            continue
        current_feature_num = get_feature_for_line(line_num)
        match_ptp_rapid = ptp_ev_pattern.match(line)
        if match_ptp_rapid and "gDblRapidSpeed" in match_ptp_rapid.group(4):
            x, y = float(match_ptp_rapid.group(2)), float(match_ptp_rapid.group(3))
            if last_x is not None:
                all_segments.append({
                    'type': 'PTP', 'line_num': line_num, 'feature_num': current_feature_num,
                    'is_printing': False, 'start_x': last_x, 'start_y': last_y, 'x': x, 'y': y,
                    'speed': 'default_rapid', 'angle': None
                })
            last_x, last_y = x, y
            continue
        if "Start gIntSubBuffer,ShutterOpen" in line or line == "OUT0.0=1":
            is_printing = True
        elif "Start gIntSubBuffer,ShutterClose" in line or line == "OUT0.0=0":
            is_printing = False
        segment = {'line_num': line_num, 'feature_num': current_feature_num, 'is_printing': is_printing, 'speed': None}
        match = ptp_e_pattern.match(line)
        if match and is_printing:
            x, y = float(match.group(2)), float(match.group(3))
            if last_x is not None:
                segment.update({'type': 'PTP', 'start_x': last_x, 'start_y': last_y, 'x': x, 'y': y, 'angle': None})
                all_segments.append(segment)
            last_x, last_y = x, y
            continue
        match = mseg_command_pattern.match(line)
        if match:
            x_mseg_start, y_mseg_start = float(match.group(2)), float(match.group(3))
            if last_x is not None and (abs(last_x - x_mseg_start) > 1e-6 or abs(last_y - y_mseg_start) > 1e-6):
                all_segments.append({
                    'type': 'PTP', 'line_num': line_num, 'feature_num': current_feature_num,
                    'is_printing': False, 'start_x': last_x, 'start_y': last_y, 'x': x_mseg_start, 'y': y_mseg_start,
                    'speed': 'default_rapid', 'angle': None
                })
            last_x, last_y = x_mseg_start, y_mseg_start
            continue
        match = mseg_line_pattern.match(line)
        if match and is_printing:
            x, y = float(match.group(2)), float(match.group(3))
            if last_x is not None:
                segment.update({'type': 'LINE', 'start_x': last_x, 'start_y': last_y, 'x': x, 'y': y, 'angle': None})
                all_segments.append(segment)
            last_x, last_y = x, y
            continue
        match = mseg_arc2_pattern.match(line)
        if match and is_printing:
            center_x, center_y, angle_rad_val = float(match.group(2)), float(match.group(3)), float(match.group(4))
            if last_x is not None:
                segment.update(
                    {'type': 'ARC2', 'start_x': last_x, 'start_y': last_y, 'center_x': center_x, 'center_y': center_y,
                     'angle': angle_rad_val})
                all_segments.append(segment)
                if abs(angle_rad_val) > 1e-6:
                    radius = np.sqrt((last_x - center_x) ** 2 + (last_y - center_y) ** 2)
                    if radius > 1e-9:
                        start_angle_rad_calc = np.arctan2(last_y - center_y, last_x - center_x)
                        end_angle_rad_calc = start_angle_rad_calc + angle_rad_val
                        last_x = center_x + radius * np.cos(end_angle_rad_calc)
                        last_y = center_y + radius * np.sin(end_angle_rad_calc)
            continue
    return all_segments


# --- ANALYSIS/GEOMETRY FUNCTIONS (No changes) ---
def get_arc_end_point(segment):
    radius = math.sqrt(
        (segment['start_x'] - segment['center_x']) ** 2 + (segment['start_y'] - segment['center_y']) ** 2)
    if radius < 1e-9: return segment['start_x'], segment['start_y']
    start_angle = math.atan2(segment['start_y'] - segment['center_y'], segment['start_x'] - segment['center_x'])
    end_angle = start_angle + segment['angle']
    end_x = segment['center_x'] + radius * math.cos(end_angle)
    end_y = segment['center_y'] + radius * math.sin(end_angle)
    return end_x, end_y


def get_arc_tangent(segment, at_start=True):
    if at_start:
        radius_vec_x = segment['start_x'] - segment['center_x']
        radius_vec_y = segment['start_y'] - segment['center_y']
    else:
        end_x, end_y = get_arc_end_point(segment)
        radius_vec_x = end_x - segment['center_x']
        radius_vec_y = end_y - segment['center_y']
    if segment['angle'] > 0:
        return -radius_vec_y, radius_vec_x
    else:
        return radius_vec_y, -radius_vec_x


def run_path_stress_analysis(parsed_segments, g_factor):
    if not parsed_segments:
        return None, [], [], {}
    G_ACCELERATION = 9800.0
    ACCEL_LIMIT = g_factor * G_ACCELERATION
    CRITICAL_TURNING_ANGLE_DEG = 1.0
    TANGENT_DOT_PRODUCT_TOLERANCE = 0.02
    stress_events = []
    arc_info_events = []
    limiting_arc_details = {}
    printing_arcs = [s for s in parsed_segments if s['is_printing'] and s['type'] == 'ARC2']
    min_radius = float('inf')
    if printing_arcs:
        for arc in printing_arcs:
            radius = math.sqrt((arc['start_x'] - arc['center_x']) ** 2 + (arc['start_y'] - arc['center_y']) ** 2)
            if 0 < radius < min_radius:
                min_radius = radius
                limiting_arc_details = {
                    'radius': radius, 'line_num': arc['line_num'], 'feature_num': arc['feature_num']
                }
    limiting_process_speed = math.sqrt(ACCEL_LIMIT * min_radius) if min_radius != float('inf') else None
    for i in range(len(parsed_segments) - 1):
        current_seg = parsed_segments[i]
        next_seg = parsed_segments[i + 1]
        if not (current_seg['is_printing'] and next_seg['is_printing']): continue
        if current_seg['type'] in ['PTP', 'LINE'] and next_seg['type'] in ['PTP', 'LINE']:
            v1_x = current_seg['x'] - current_seg['start_x'];
            v1_y = current_seg['y'] - current_seg['start_y']
            v2_x = next_seg['x'] - next_seg['start_x'];
            v2_y = next_seg['y'] - next_seg['start_y']
            mag_v1 = math.sqrt(v1_x ** 2 + v1_y ** 2);
            mag_v2 = math.sqrt(v2_x ** 2 + v2_y ** 2)
            if mag_v1 > 1e-6 and mag_v2 > 1e-6:
                dot = (v1_x * v2_x) + (v1_y * v2_y)
                angle = math.degrees(math.acos(min(1.0, max(-1.0, dot / (mag_v1 * mag_v2)))))
                if angle >= CRITICAL_TURNING_ANGLE_DEG:
                    stress_events.append({'type': 'Line-to-Line', 'line_num': next_seg['line_num'],
                                          'feature_num': next_seg['feature_num'],
                                          'coords': (next_seg['start_x'], next_seg['start_y']),
                                          'message': f"Sharp turn of {angle:.1f} degrees detected."})
        if current_seg['type'] in ['PTP', 'LINE'] and next_seg['type'] == 'ARC2':
            v_line_x = current_seg['x'] - current_seg['start_x'];
            v_line_y = current_seg['y'] - current_seg['start_y']
            v_rad_x = next_seg['start_x'] - next_seg['center_x'];
            v_rad_y = next_seg['start_y'] - next_seg['center_y']
            mag_line = math.sqrt(v_line_x ** 2 + v_line_y ** 2);
            mag_rad = math.sqrt(v_rad_x ** 2 + v_rad_y ** 2)
            if mag_line > 1e-6 and mag_rad > 1e-6 and abs(((v_line_x * v_rad_x) + (v_line_y * v_rad_y)) / (
                    mag_line * mag_rad)) > TANGENT_DOT_PRODUCT_TOLERANCE:
                stress_events.append({'type': 'Line-Arc Stress', 'line_num': next_seg['line_num'],
                                      'feature_num': next_seg['feature_num'],
                                      'coords': (next_seg['start_x'], next_seg['start_y']),
                                      'message': "Non-tangential transition from a line into an arc."})
        if current_seg['type'] == 'ARC2' and next_seg['type'] in ['PTP', 'LINE']:
            t_x, t_y = get_arc_tangent(current_seg, at_start=False)
            l_x = next_seg['x'] - next_seg['start_x'];
            l_y = next_seg['y'] - next_seg['start_y']
            mag_t = math.sqrt(t_x ** 2 + t_y ** 2);
            mag_l = math.sqrt(l_x ** 2 + l_y ** 2)
            if mag_t > 1e-6 and mag_l > 1e-6 and abs(
                    abs(((t_x * l_x) + (t_y * l_y)) / (mag_t * mag_l)) - 1.0) > TANGENT_DOT_PRODUCT_TOLERANCE:
                stress_events.append({'type': 'Line-Arc Stress', 'line_num': next_seg['line_num'],
                                      'feature_num': next_seg['feature_num'],
                                      'coords': (next_seg['start_x'], next_seg['start_y']),
                                      'message': "Non-tangential transition from an arc into a line."})
        if current_seg['type'] == 'ARC2' and next_seg['type'] == 'ARC2':
            t1_x, t1_y = get_arc_tangent(current_seg, at_start=False)
            t2_x, t2_y = get_arc_tangent(next_seg, at_start=True)
            mag_t1 = math.sqrt(t1_x ** 2 + t1_y ** 2);
            mag_t2 = math.sqrt(t2_x ** 2 + t2_y ** 2)
            if mag_t1 > 1e-6 and mag_t2 > 1e-6:
                dot = (t1_x * t2_x) + (t1_y * t2_y)
                angle = math.degrees(math.acos(min(1.0, max(-1.0, dot / (mag_t1 * mag_t2)))))
                if angle > CRITICAL_TURNING_ANGLE_DEG and angle < (180 - CRITICAL_TURNING_ANGLE_DEG):
                    stress_events.append({'type': 'Arc-to-Arc Stress', 'line_num': next_seg['line_num'],
                                          'feature_num': next_seg['feature_num'],
                                          'coords': (next_seg['start_x'], next_seg['start_y']),
                                          'message': f"Non-collinear transition between arcs. Angle: {angle:.1f} degrees."})
    if limiting_process_speed is not None:
        for arc in printing_arcs:
            radius = math.sqrt((arc['start_x'] - arc['center_x']) ** 2 + (arc['start_y'] - arc['center_y']) ** 2)
            if radius > 1e-6:
                accel_at_limit_speed = (limiting_process_speed ** 2) / radius
                status = "At Limit" if abs(accel_at_limit_speed - ACCEL_LIMIT) < 1.0 else "Below Limit"
                arc_info_events.append({
                    'type': 'Arc Acceleration Info', 'line_num': arc['line_num'], 'feature_num': arc['feature_num'],
                    'message': f"At {limiting_process_speed:.1f} mm/s, this arc experiences {accel_at_limit_speed:.1f} mm/s^2 ({status})."
                })
    return limiting_process_speed, stress_events, arc_info_events, limiting_arc_details


# --- REPORTING FUNCTIONS (No changes) ---
def generate_analysis_report(limiting_speed, stress_events, g_factor, limiting_arc_details):
    report_lines = []
    report_lines.append("--- Path Analysis Report ---")
    if limiting_speed:
        report_lines.append(f"Limiting Process Speed (based on G-Factor={g_factor}): {limiting_speed:.2f} mm/s")
        if limiting_arc_details:
            report_lines.append(
                f" -> This speed is limited by an arc in Feature {limiting_arc_details['feature_num']}.")
    else:
        report_lines.append("No arcs found; could not determine a limiting process speed.")
    report_lines.append("")
    test_types = ['Line-to-Line', 'Line-Arc Stress', 'Arc-to-Arc Stress']
    for test_type in test_types:
        report_lines.append(f"[--- {test_type} Analysis ---]")
        events = [e for e in stress_events if e['type'] == test_type]
        if events:
            for event in events:
                report_lines.append(
                    f"  [WARNING] Feature {event['feature_num']} at ({event['coords'][0]:.3f}, {event['coords'][1]:.3f}): {event['message']}")
        else:
            report_lines.append(f"  No potential stress points detected for this category.")
        report_lines.append("")
    report_lines.append("--- End of Path Analysis ---")
    return "\n".join(report_lines)


def create_annotated_prg_file(original_filename, annotated_filename, limiting_speed, stress_events, arc_info_events,
                              g_factor, limiting_arc_details):
    annotations = {}
    for event in stress_events + arc_info_events:
        line_num = event['line_num']
        prefix = "! [STRESS WARNING]" if event in stress_events else "! [INFO]"
        message = f"{prefix} {event['message']}"
        if line_num not in annotations: annotations[line_num] = []
        annotations[line_num].append(message)
    try:
        with open(original_filename, 'r') as infile, open(annotated_filename, 'w') as outfile:
            outfile.write("! --- ANALYSIS SUMMARY ---\n")
            if limiting_speed:
                accel_limit = g_factor * 9800.0
                outfile.write(f"! Max Safe Process Speed (for G-Factor={g_factor}): {limiting_speed:.2f} mm/s\n")
                if limiting_arc_details:
                    outfile.write(
                        f"! -> Limited by arc with radius {limiting_arc_details['radius']:.4f} mm in Feature {limiting_arc_details['feature_num']}.\n")
                outfile.write(f"! Corresponding Max Centripetal Acceleration: {accel_limit:.1f} mm/s^2\n")
            else:
                outfile.write("! No arcs found in design to calculate a limiting speed.\n")
            outfile.write("! Geometric stress warnings are independent of speed.\n")
            outfile.write("! Arc acceleration info is calculated using the max safe speed.\n")
            outfile.write("! ------------------------\n\n")
            for i, line in enumerate(infile, 1):
                outfile.write(line)
                if i in annotations:
                    for msg in annotations[i]:
                        outfile.write(f"{msg}\n")
    except Exception as e:
        raise Exception(f"Could not create annotated file. Error: {e}")


# --- ANIMATION FUNCTIONS (MODIFIED) ---
def interpolate_arc(start_x, start_y, center_x, center_y, angle_rad, num_points=30):
    radius = np.sqrt((start_x - center_x) ** 2 + (start_y - center_y) ** 2)
    if radius < 1e-9:
        return [(start_x, start_y)] * num_points
    start_angle_rad_calc = np.arctan2(start_y - center_y, start_x - center_x)
    end_angle_rad_calc = start_angle_rad_calc + angle_rad
    theta = np.linspace(start_angle_rad_calc, end_angle_rad_calc, num_points)
    arc_x_points = center_x + radius * np.cos(theta)
    arc_y_points = center_y + radius * np.sin(theta)
    return list(zip(arc_x_points, arc_y_points))


def animate_printer(filename_to_simulate, limiting_speed, animation_save_path):
    """
    Animates the toolpath and saves it to a file.
    Returns the path to the saved animation file.
    """
    segments = parse_prg_file(filename_to_simulate)
    if not segments:
        return None  # Return None if no segments to draw

    fig, ax = plt.subplots(figsize=(10, 8))
    all_x, all_y = [], []
    for seg in segments:
        if 'start_x' in seg: all_x.extend([seg['start_x']])
        if 'start_y' in seg: all_y.extend([seg['start_y']])
        if seg['type'] == 'ARC2':
            arc_points = interpolate_arc(seg['start_x'], seg['start_y'], seg['center_x'], seg['center_y'], seg['angle'])
            if arc_points:
                all_x.extend([p[0] for p in arc_points]);
                all_y.extend([p[1] for p in arc_points])
        elif 'x' in seg:
            all_x.extend([seg['x']]);
            all_y.extend([seg['y']])

    if not all_x or not all_y:
        ax.set_xlim(-5, 10);
        ax.set_ylim(-2, 10)
    else:
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        x_range = max_x - min_x if max_x > min_x else 2.0
        y_range = max_y - min_y if max_y > min_y else 2.0
        padding_x = x_range * 0.1;
        padding_y = y_range * 0.1
        ax.set_xlim(min_x - max(1.0, padding_x), max_x + max(1.0, padding_x))
        ax.set_ylim(min_y - max(1.0, padding_y), max_y + max(1.0, padding_y))

    ax.set_xlabel("X Position (mm)");
    ax.set_ylabel("Y Position (mm)")
    ax.set_title(f"Aerosol Jet Printer Simulation ({os.path.basename(filename_to_simulate)})")
    ax.set_aspect('equal', adjustable='box');
    ax.grid(True, linestyle='--', alpha=0.7)

    head_dot = ax.plot([], [], 'yo', markersize=7, markeredgecolor='k', zorder=10)[0]
    info_text = ax.text(0.02, 0.98, '', transform=ax.transAxes, fontsize=9, verticalalignment='top',
                        bbox=dict(boxstyle="round,pad=0.3", fc="lightgoldenrodyellow", alpha=0.85))

    def init():
        head_dot.set_data([], [])
        if segments and 'start_x' in segments[0]:
            head_dot.set_data([segments[0]['start_x']], [segments[0]['start_y']])
        info_text.set_text('Starting...')
        return [head_dot, info_text]

    def update(frame_idx):
        if frame_idx >= len(segments):
            info_text.set_text('Animation Complete')
            return [head_dot, info_text]
        seg = segments[frame_idx]
        if 'start_x' not in seg: return [head_dot, info_text]
        end_x, end_y = None, None
        if seg['type'] == 'ARC2':
            arc_pts = interpolate_arc(seg['start_x'], seg['start_y'], seg['center_x'], seg['center_y'], seg['angle'])
            if arc_pts:
                ax.plot([p[0] for p in arc_pts], [p[1] for p in arc_pts], 'r-' if seg['is_printing'] else 'b--',
                        linewidth=2.0 if seg['is_printing'] else 1.2, alpha=0.8)
                end_x, end_y = arc_pts[-1]
        elif 'x' in seg:
            ax.plot([seg['start_x'], seg['x']], [seg['start_y'], seg['y']], 'r-' if seg['is_printing'] else 'b--',
                    linewidth=2.0 if seg['is_printing'] else 1.2, alpha=0.8)
            end_x, end_y = seg['x'], seg['y']
        if end_x is not None: head_dot.set_data([end_x], [end_y])
        speed_display = f"{limiting_speed:.1f} mm/s (Limit)" if seg[
                                                                    'is_printing'] and limiting_speed is not None else "Default Rapid"
        status_text = "Printing" if seg['is_printing'] else "Rapid Move"
        info_text.set_text(f"Feature: {seg.get('feature_num', 'N/A')}\n{status_text}\nSpeed: {speed_display}")
        return [head_dot, info_text]

    # --- THIS IS THE KEY CHANGE ---
    # Instead of plt.show(), we create the animation object
    ani = animation.FuncAnimation(fig, update, frames=len(segments) + 1, init_func=init, blit=False, interval=50,
                                  repeat=False)

    # And save it to the path provided
    ani.save(animation_save_path, writer='ffmpeg', fps=15)

    # Close the plot to free up memory on the server
    plt.close(fig)

    # Return the path to the video file
    return animation_save_path