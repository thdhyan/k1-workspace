The robot contract other libraries import. It has no heavy dependencies.

```python
from k1_common.paths import models_dir, model   # $K1_MODELS_DIR, default ~/k1_models
ckpt = model("mjlab_k1/walk_still_v2/model_8998.pt")
from k1_common import clip_schema                 # motion-clip schema shared with k1-mimic
```
`ros/k1_interfaces` is the ROS 2 message package. Build it with colcon from k1-deploy-laptop's workspace.
