import os
import sys

from pathlib import Path
import tokenizers
import keras

# TODO(guy): review this change.
# from .model import load_model, Moonshine
# from . import ASSETS_DIR
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from model import load_model, Moonshine


def load_audio(audio, return_numpy=False):
    if isinstance(audio, (str, Path)):
        import librosa

        audio, _ = librosa.load(audio, sr=16_000)
        if return_numpy:
            return audio[None, ...]
        audio = keras.ops.expand_dims(keras.ops.convert_to_tensor(audio), 0)
    return audio


def assert_audio_size(audio):
    assert len(keras.ops.shape(audio)) == 2, "audio should be of shape [batch, samples]"
    num_seconds = keras.ops.convert_to_numpy(keras.ops.size(audio) / 16_000)
    assert (
        0.1 < num_seconds < 64
    ), "Moonshine models support audio segments that are between 0.1s and 64s in a single transcribe call. For transcribing longer segments, pre-segment your audio and provide shorter segments."
    return num_seconds


def transcribe(audio, model="moonshine/base"):
    if isinstance(model, str):
        model = load_model(model)
    assert isinstance(
        model, Moonshine
    ), f"Expected a Moonshine model or a model name, not a {type(model)}"

    audio = load_audio(audio)
    assert_audio_size(audio)

    tokens = model.generate(audio)
    return load_tokenizer().decode_batch(tokens)


def transcribe_with_onnx(audio, model="moonshine/base"):
    from .onnx_model import MoonshineOnnxModel

    if isinstance(model, str):
        model = MoonshineOnnxModel(model_name=model)
    assert isinstance(
        model, MoonshineOnnxModel
    ), f"Expected a MoonshineOnnxModel model or a model name, not a {type(model)}"
    audio = load_audio(audio, return_numpy=True)
    assert_audio_size(audio)

    tokens = model.generate(audio)
    return load_tokenizer().decode_batch(tokens)


def load_tokenizer():
    # TODO(guy): review this change.
    # tokenizer_file = ASSETS_DIR / "tokenizer.json"
    assets_dir = f"{os.path.join(os.path.dirname(__file__), 'assets')}"
    tokenizer_file = f"{assets_dir}{os.sep}tokenizer.json"
    tokenizer = tokenizers.Tokenizer.from_file(str(tokenizer_file))
    return tokenizer


def benchmark(audio, model="moonshine/base"):
    import time

    if isinstance(model, str):
        model = load_model(model)
    assert isinstance(
        model, Moonshine
    ), f"Expected a Moonshine model or a model name, not a {type(model)}"

    audio = load_audio(audio)
    num_seconds = assert_audio_size(audio)

    print("Warming up...")
    for _ in range(4):
        _ = model.generate(audio)

    print("Benchmarking...")
    N = 8
    start_time = time.time_ns()
    for _ in range(N):
        _ = model.generate(audio)
    end_time = time.time_ns()

    elapsed_time = (end_time - start_time) / N
    elapsed_time /= 1e6

    print(f"Time to transcribe {num_seconds:.2f}s of speech is {elapsed_time:.2f}ms")
