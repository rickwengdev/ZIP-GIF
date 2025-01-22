import os
import threading
from tkinter import Tk, Label, Button, Entry, filedialog, Text, Scrollbar, Canvas
from PIL import Image, ImageSequence, ImageTk
from datetime import datetime

# Global variables to control compression and preview states
running = False  # Controls whether compression is running
preview_refreshing = False  # Controls whether GIF preview is refreshing


def compress_gif(input_path, output_path, max_size_kb=256, initial_resolution=(128, 128), resolution_step=8,
                 fps_reduction_step=2, min_resolution=(32, 32), log_callback=None, preview_callback=None, finish_callback=None):
    """Compress a GIF file to meet a size constraint."""
    global running
    max_size_bytes = max_size_kb * 1024
    current_resolution = initial_resolution
    temp_output_path = "temp_compressed.gif"

    try:
        with Image.open(input_path) as img:
            original_duration = img.info.get('duration', 100)
            original_fps = 1000 / original_duration if original_duration else 10
            current_fps = original_fps

            while running:
                frames = []
                frame_count = 0

                # Process each frame in the GIF
                for frame in ImageSequence.Iterator(img):
                    frame = frame.resize(current_resolution, Image.Resampling.LANCZOS)
                    frame = frame.convert("P", palette=Image.ADAPTIVE)
                    if frame_count % max(1, round(original_fps / current_fps)) == 0:
                        frames.append(frame)
                    frame_count += 1

                # Save the frames to a temporary GIF file
                frames[0].save(temp_output_path, save_all=True, append_images=frames[1:], optimize=True, loop=0)
                file_size = os.path.getsize(temp_output_path)

                if log_callback:
                    log_callback(f"Size: {file_size / 1024:.2f} KB | Resolution: {current_resolution} | FPS: {current_fps}")

                if preview_callback:
                    preview_callback(temp_output_path)

                # Check if the file meets the size constraint
                if file_size <= max_size_bytes:
                    os.rename(temp_output_path, output_path)
                    if log_callback:
                        log_callback(f"Compression successful! Output saved to {output_path}")
                    break

                # Adjust resolution or FPS for further compression
                if current_resolution[0] > min_resolution[0] and current_resolution[1] > min_resolution[1]:
                    current_resolution = (
                        max(min_resolution[0], current_resolution[0] - resolution_step),
                        max(min_resolution[1], current_resolution[1] - resolution_step)
                    )
                else:
                    if current_fps > fps_reduction_step:
                        current_fps -= fps_reduction_step
                    else:
                        if log_callback:
                            log_callback("Cannot compress further without degrading quality excessively.")
                        break
    except Exception as e:
        if log_callback:
            log_callback(f"Error: {e}")
    finally:
        running = False
        if finish_callback:
            finish_callback(output_path)


def toggle_compression():
    """Toggle the compression process on or off."""
    global running, preview_refreshing
    if running:
        running = False
        start_button.config(text="Start")
    else:
        running = True
        preview_refreshing = False  # Stop preview during compression
        start_button.config(text="Stop")
        start_compression_thread()


def start_compression_thread():
    """Start the compression process in a separate thread."""
    input_path = input_path_entry.get()
    output_path = output_path_entry.get()
    max_size = int(max_size_entry.get())
    resolution = tuple(map(int, resolution_entry.get().split(',')))
    min_resolution = tuple(map(int, min_resolution_entry.get().split(',')))
    step_px = int(step_entry.get())

    if not os.path.exists(input_path):
        log_message("Input file does not exist.")
        return

    log_message("Starting compression...")
    threading.Thread(
        target=compress_gif,
        args=(input_path, output_path, max_size),
        kwargs={
            "initial_resolution": resolution,
            "resolution_step": step_px,
            "min_resolution": min_resolution,
            "log_callback": log_message,
            "preview_callback": show_preview,
            "finish_callback": on_compression_finished,
        },
    ).start()


def on_compression_finished(final_output_path):
    """Callback when compression is finished or stopped."""
    global preview_refreshing
    preview_refreshing = True  # Re-enable preview after compression
    start_button.config(text="Start")
    log_message("Compression finished.")
    show_preview(final_output_path)


def select_file(entry, preview_callback):
    """Open a file dialog to select a file and update the entry widget."""
    file_path = filedialog.askopenfilename(filetypes=[("GIF Files", "*.gif")])
    entry.delete(0, "end")
    entry.insert(0, file_path)
    preview_callback(file_path)


def save_file(entry):
    """Open a save dialog to select the output file path."""
    file_path = filedialog.asksaveasfilename(defaultextension=".gif", filetypes=[("GIF Files", "*.gif")])
    entry.delete(0, "end")
    entry.insert(0, file_path)


def show_preview(file_path):
    """Display the GIF in the preview canvas."""
    global preview_refreshing
    try:
        with Image.open(file_path) as img:
            frames = [ImageTk.PhotoImage(frame.resize((100, 100), Image.Resampling.LANCZOS)) for frame in ImageSequence.Iterator(img)]
        preview_canvas.delete("all")
        frame_id = preview_canvas.create_image(50, 50, image=frames[0])
        preview_canvas.image_frames = frames
        preview_canvas.current_frame = 0

        def update_preview():
            if not preview_refreshing:
                return
            frame_index = preview_canvas.current_frame
            preview_canvas.itemconfig(frame_id, image=preview_canvas.image_frames[frame_index])
            preview_canvas.current_frame = (frame_index + 1) % len(preview_canvas.image_frames)
            root.after(100, update_preview)

        preview_refreshing = True
        update_preview()
    except Exception as e:
        log_message(f"Error loading preview: {e}")


def log_message(message):
    """Log a message with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_output.insert("end", f"[{timestamp}] {message}\n")
    log_output.see("end")


# GUI setup
root = Tk()
root.title("GIF Compressor")
root.geometry("450x650")

# Input file selection
Label(root, text="Input File:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
input_path_entry = Entry(root, width=40)
input_path_entry.grid(row=0, column=1, columnspan=2, padx=10)
Button(root, text="Browse", command=lambda: select_file(input_path_entry, show_preview)).grid(row=0, column=3, padx=10)

# Output file selection
Label(root, text="Output File:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
output_path_entry = Entry(root, width=40)
output_path_entry.grid(row=1, column=1, columnspan=2, padx=10)
Button(root, text="Save As", command=lambda: save_file(output_path_entry)).grid(row=1, column=3, padx=10)

# Compression parameters
Label(root, text="Max Size (KB):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
max_size_entry = Entry(root, width=10)
max_size_entry.insert(0, "256")
max_size_entry.grid(row=2, column=1, sticky="w")

Label(root, text="Resolution (WxH):").grid(row=2, column=2, sticky="w", padx=10, pady=5)
resolution_entry = Entry(root, width=10)
resolution_entry.insert(0, "128,128")
resolution_entry.grid(row=2, column=3, sticky="w")

Label(root, text="Min Resolution:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
min_resolution_entry = Entry(root, width=10)
min_resolution_entry.insert(0, "32,32")
min_resolution_entry.grid(row=3, column=1, sticky="w")

Label(root, text="Step (px):").grid(row=3, column=2, sticky="w", padx=10, pady=5)
step_entry = Entry(root, width=10)
step_entry.insert(0, "8")
step_entry.grid(row=3, column=3, sticky="w")

# GIF preview
Label(root, text="GIF Preview:").grid(row=4, column=0, columnspan=4, pady=10)
preview_canvas = Canvas(root, width=100, height=100, bg="white", highlightthickness=1, highlightbackground="black")
preview_canvas.grid(row=5, column=0, columnspan=4, pady=5)

# Log output
Label(root, text="Log Output:").grid(row=6, column=0, columnspan=4, pady=10)
scrollbar = Scrollbar(root)
log_output = Text(root, height=10, width=55, yscrollcommand=scrollbar.set)
scrollbar.config(command=log_output.yview)
scrollbar.grid(row=7, column=4, sticky="ns")
log_output.grid(row=7, column=0, columnspan=4, padx=10)

# Start/Stop button
start_button = Button(root, text="Start", command=toggle_compression, width=15)
start_button.grid(row=8, column=0, columnspan=4, pady=10)

# Main loop
root.mainloop()