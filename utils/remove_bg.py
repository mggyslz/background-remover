from rembg import remove, new_session
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np


def remove_background(input_path, output_path, mode='best'):
    """
    Remove background using different models depending on mode.
    Modes:
        - best (high quality ISNet)
        - portrait (human segmentation)
        - fast (u2netp)
    """
    input_img = Image.open(input_path)

    # Convert to RGB if needed
    if input_img.mode not in ('RGB', 'RGBA'):
        input_img = input_img.convert('RGB')

    # Upscale small images for better quality
    original_size = input_img.size
    min_dimension = min(original_size)
    if min_dimension < 1024:
        scale_factor = 1024 / min_dimension
        new_size = (
            int(original_size[0] * scale_factor),
            int(original_size[1] * scale_factor)
        )
        input_img = input_img.resize(new_size, Image.LANCZOS)

    # Slight sharpening to improve mask quality
    input_img = ImageEnhance.Sharpness(input_img).enhance(1.2)

    # Select model + parameters
    if mode == 'portrait':
        model = 'u2net_human_seg'
        fg_threshold = 250
        bg_threshold = 5
        erode_size = 15
    elif mode == 'fast':
        model = 'u2netp'
        fg_threshold = 240
        bg_threshold = 10
        erode_size = 10
    else:  # best
        model = 'isnet-general-use'
        fg_threshold = 270
        bg_threshold = 20
        erode_size = 12

    # Create session (IMPORTANT FIX)
    session = new_session(model_name=model)

    # Background removal
    output = remove(
        input_img,
        session=session,
        alpha_matting=True,
        alpha_matting_foreground_threshold=fg_threshold,
        alpha_matting_background_threshold=bg_threshold,
        alpha_matting_erode_size=erode_size,
        post_process_mask=True,
        bgcolor=None
    )

    # Resize back if upscaled
    if input_img.size != original_size:
        output = output.resize(original_size, Image.LANCZOS)

    # Edge refinement
    output = refine_edges(output)

    # Force PNG
    if not output_path.lower().endswith(".png"):
        output_path = output_path.rsplit(".", 1)[0] + ".png"

    # Save
    output.save(output_path, 'PNG', optimize=False, compress_level=1)
    return output_path


def refine_edges(img):
    """Smooth edges by softening alpha channel."""
    if img.mode != 'RGBA':
        return img

    r, g, b, a = img.split()
    a = a.filter(ImageFilter.GaussianBlur(radius=0.5))
    return Image.merge('RGBA', (r, g, b, a))


def remove_background_with_feather(input_path, output_path, feather_amount=2):
    """
    Remove background using ISNet and feather edges for soft transitions.
    """
    input_img = Image.open(input_path)

    if input_img.mode not in ('RGB', 'RGBA'):
        input_img = input_img.convert('RGB')

    # Session for ISNet
    session = new_session(model_name='isnet-general-use')

    output = remove(
        input_img,
        session=session,
        alpha_matting=True,
        alpha_matting_foreground_threshold=270,
        alpha_matting_background_threshold=20,
        alpha_matting_erode_size=12,
        post_process_mask=True
    )

    # Feather alpha channel
    if output.mode == 'RGBA':
        r, g, b, a = output.split()
        a = a.filter(ImageFilter.GaussianBlur(radius=feather_amount))
        output = Image.merge('RGBA', (r, g, b, a))

    if not output_path.lower().endswith(".png"):
        output_path = output_path.rsplit(".", 1)[0] + ".png"

    output.save(output_path, 'PNG', optimize=False, compress_level=1)
    return output_path


def remove_background_advanced(input_path, output_path):
    """
    Advanced multi-pass removal using ISNet + U2Net with mask blending.
    """
    input_img = Image.open(input_path)

    if input_img.mode not in ('RGB', 'RGBA'):
        input_img = input_img.convert('RGB')

    # First pass — ISNet
    session1 = new_session(model_name='isnet-general-use')
    output1 = remove(
        input_img,
        session=session1,
        alpha_matting=True,
        alpha_matting_foreground_threshold=270,
        alpha_matting_background_threshold=20,
        alpha_matting_erode_size=12,
        post_process_mask=True
    )

    # Second pass — U2Net refinement
    session2 = new_session(model_name='u2net')
    output2 = remove(
        input_img,
        session=session2,
        alpha_matting=True,
        alpha_matting_foreground_threshold=260,
        alpha_matting_background_threshold=15,
        alpha_matting_erode_size=10,
        post_process_mask=True
    )

    # Blend masks using max(alpha)
    if output1.mode == 'RGBA' and output2.mode == 'RGBA':
        r1, g1, b1, a1 = output1.split()
        _, _, _, a2 = output2.split()

        a1_np = np.array(a1)
        a2_np = np.array(a2)

        blended_alpha = Image.fromarray(np.maximum(a1_np, a2_np).astype('uint8'))

        output = Image.merge('RGBA', (r1, g1, b1, blended_alpha))
    else:
        output = output1

    # Edge refinement
    output = refine_edges(output)

    if not output_path.lower().endswith(".png"):
        output_path = output_path.rsplit(".", 1)[0] + ".png"

    output.save(output_path, 'PNG', optimize=False, compress_level=1)
    return output_path
