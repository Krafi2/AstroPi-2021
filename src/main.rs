use image::{EncodableLayout, ImageBuffer, ImageEncoder, Rgb};
use rayon::prelude::*;
use show_image::{
    create_window,
    event::{ElementState, VirtualKeyCode, WindowEvent},
    ImageInfo, ImageView,
};
use std::{
    env::args, error::Error, fs::File, io::BufWriter, path::PathBuf, sync::Arc, time::Duration,
};

#[show_image::main]
fn main() -> Result<(), Box<dyn Error>> {
    let save_sequence = std::env::var("CAPTURE_SEQUENCE").is_ok();

    let image_dir = args().nth(1).unwrap();
    let out_dir = PathBuf::from(args().nth(2).unwrap());
    let mut a = std::fs::read_dir(image_dir)?.collect::<Result<Vec<_>, _>>()?;

    a.sort_by_key(|f| f.file_name());

    let (w, h) = image::image_dimensions(a[0].path())?;

    let start = std::env::var("START_AT")
        .map(|s| s.parse::<usize>().unwrap())
        .unwrap_or(0);

    let a = &a[start..];

    let mut image1 = image::open(a[0].path())?.into_rgb8();
    let mut result = ImageBuffer::<Rgb<u8>, _>::new(0, 0);

    let window = create_window("image", Default::default())?;

    for img in &a[1..] {
        let image2 = image::open(img.path())?.into_rgb8();

        process_image(&image1, &image2, &mut result, w, h, 128);

        let view = ImageView::new(
            ImageInfo::rgb8(result.width(), result.height()),
            result.as_bytes(),
        );
        window.set_image("image-001", view)?;

        let _ = std::mem::replace(&mut image1, image2);

        let mut save = save_sequence;
        'cock: loop {
            loop {
                match window.event_channel()?.try_recv() {
                    Ok(WindowEvent::KeyboardInput(e)) => {
                        if e.input.state == ElementState::Pressed {
                            match e.input.key_code {
                                Some(VirtualKeyCode::Escape) => return Ok(()),
                                Some(VirtualKeyCode::S) => {
                                    save = true;
                                }
                                _ => break 'cock,
                            }
                        }
                    }
                    Ok(_) => {}
                    Err(_) => break,
                }
            }
            if save_sequence {
                break;
            }
            std::thread::sleep(Duration::from_millis(16));
        }

        if save {
            let path = out_dir
                .join(img.path().file_name().unwrap())
                .with_extension("png");
            println!("Saving image to '{}'", path.to_string_lossy());
            let file = File::create(path)?;
            let encoder = image::codecs::png::PngEncoder::new(BufWriter::new(file));
            ImageEncoder::write_image(
                encoder,
                result.as_bytes(),
                result.width(),
                result.height(),
                image::ColorType::Rgb8,
            )?;
        }
    }

    Ok(())
}

// https://en.wikipedia.org/wiki/Block-matching_algorithm
fn process_image(
    img1: &ImageBuffer<Rgb<u8>, Vec<u8>>,
    img2: &ImageBuffer<Rgb<u8>, Vec<u8>>,
    res: &mut ImageBuffer<Rgb<u8>, Vec<u8>>,
    w: u32,
    h: u32,
    p: i32,
) {
    const BS: usize = 16;
    let rw = (w + BS as u32 - 1) / BS as u32;
    let rh = (h + BS as u32 - 1) / BS as u32;
    if res.width() != rw || res.height() != rh {
        *res = ImageBuffer::new(rw, rh);
    }
    // const MAX_MAD: u32 = (BS*BS*3*255) as u32 / 3;

    struct Crimes<T>(*mut T);
    unsafe impl<T> Send for Crimes<T> {}
    unsafe impl<T> Sync for Crimes<T> {}

    let res = Arc::new(Crimes(res as *mut ImageBuffer<Rgb<u8>, Vec<u8>>));

    (0..h).into_par_iter().step_by(BS).for_each(|yo| {
        for xo in (0..w).step_by(BS) {
            let mut b1 = [[image::Rgb([0, 0, 0]); BS]; BS];
            // copy the reference tile
            for (yi, y) in (yo..(yo + BS as u32).min(h - 1)).enumerate() {
                for (xi, x) in (xo..(xo + BS as u32).min(w - 1)).enumerate() {
                    b1[yi][xi] = img1[(x, y)];
                }
            }

            // best MAD, x index, y index
            let mut best = (u32::MAX, 0, 0);
            for yp in yo as i32 - p as i32..yo as i32 + p as i32 {
                for xp in xo as i32 - p as i32..xo as i32 + p as i32 {
                    let mut b2 = [[image::Rgb([0, 0, 0]); BS]; BS];
                    // copy the search tile
                    for y in 0..BS {
                        let yf = y as i32 + yp;
                        if yf < 0 {
                            continue;
                        } else if yf >= h as i32 {
                            break;
                        }
                        for x in 0..BS {
                            let xf = x as i32 + xp;
                            if xf < 0 {
                                continue;
                            } else if xf >= w as i32 {
                                break;
                            }

                            b2[y][x] = img2[(xf as _, yf as _)];
                        }
                    }
                    // calculate the mean absolute difference
                    let mut acc = 0;
                    for y in 0..BS {
                        for x in 0..BS {
                            acc += b1[y][x][0].abs_diff(b2[y][x][0]) as u32;
                            acc += b1[y][x][1].abs_diff(b2[y][x][1]) as u32;
                            acc += b1[y][x][2].abs_diff(b2[y][x][2]) as u32;
                        }
                    }
                    if acc < best.0 {
                        best = (acc, xp - xo as i32, yp - yo as i32);
                    }
                }
            }
            let out = image::Rgb([best.1 as u8, best.2 as u8, 0]);
            unsafe {
                // ohoho pinkie swear that our writes don't alias
                (*(*res).0)[(xo / BS as u32, yo / BS as u32)] = out;
            }
        }
    });
}
