import os
import numpy as np

PIP = ["onnx", "onnxruntime"]
ANSWERS = {"M1": 3, "M2": 17, "M3": 2}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Synchronization and tensor copies across the boundary, both directions",
    "Layout and precision conversions, plus slow CPU execution while the accelerator idles",
    "Fix: rebuild the operator from supported ones or move it to post-processing",
    "Fix: custom kernel or plugin (TensorRT plugin, delegate custom op) or change the export so it is recognized",
]}
HINTS = {
    "onnx": "torch.onnx.export(..., dynamo=False); session.run(None, {session.get_inputs()[0].name: x})[0].",
    "fallback": "Walk the ops; append to the last segment if the device matches, else start a new one.",
    "dma": "First line = addr // line * line; last line = (addr + size - 1) // line * line.",
}


def check_onnx(export, run):
    import torch
    torch.manual_seed(0)
    net = torch.nn.Sequential(torch.nn.Conv2d(3, 8, 3, padding=1), torch.nn.ReLU(), torch.nn.AdaptiveAvgPool2d(1),
                              torch.nn.Flatten(), torch.nn.Linear(8, 4)).eval()
    x = torch.randn(1, 3, 16, 16)
    path = export(net, x, os.path.abspath("check_net.onnx"))
    assert os.path.exists(path), "export must write the file and return its path"
    import onnx
    onnx.checker.check_model(onnx.load(path))
    y = run(path, x.numpy())
    with torch.no_grad():
        ref = net(x).numpy()
    assert y.shape == ref.shape and np.allclose(y, ref, atol=1e-5), "ONNX Runtime output differs from PyTorch"


def check_fallback(partition):
    ops = ["conv", "relu", "conv", "nms", "conv", "relu", "softmax"]
    segs = partition(ops, {"conv", "relu", "softmax"})
    assert [(d, list(o)) for d, o in segs] == [("npu", ["conv", "relu", "conv"]), ("cpu", ["nms"]), ("npu", ["conv", "relu", "softmax"])]
    assert [d for d, _ in partition(["a", "b"], set())] == ["cpu"] and partition([], {"a"}) == []


def check_dma(lines, maintenance):
    got = lines(0x20000020, 1024)
    assert len(got) == 17 and got[0] == 0x20000000 and got[-1] == 0x20000400, f"{len(got)} lines from {hex(got[0])}"
    assert len(lines(0x20000000, 1024)) == 16 and lines(100, 1) == [64] and lines(0, 0) == []
    assert maintenance("to_device") == "clean" and maintenance("from_device") == "invalidate"
