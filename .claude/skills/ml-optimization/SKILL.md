---
name: ml-optimization
description: Machine learning model optimization, training pipelines, and experiment tracking. Use when working with PyTorch, TensorFlow, JAX, ONNX, or any ML model training, evaluation, or deployment.
---

# ML Optimization & Training Skill

## When to Use
- Training neural networks or ML models
- Optimizing model performance (speed, accuracy, memory)
- Setting up experiment tracking
- Debugging training issues (loss not converging, gradients exploding)
- Model deployment and serving

## Core Patterns

### Training Loop Best Practices
```python
# Always use:
# 1. Mixed precision training (AMP) for speed
# 2. Gradient clipping for stability
# 3. Learning rate scheduling
# 4. Proper checkpointing
# 5. Experiment tracking (W&B, MLflow, TensorBoard)
```

### Model Optimization Techniques
1. **Quantization** - INT8/FP16 for inference speed
2. **Pruning** - Remove unnecessary weights
3. **Knowledge Distillation** - Smaller student models
4. **ONNX Export** - Cross-framework deployment
5. **TorchScript/TensorRT** - Production compilation

### Debugging Checklist
- [ ] Check data pipeline (shapes, normalization, shuffling)
- [ ] Verify loss function matches task
- [ ] Monitor gradient norms (watch for NaN/Inf)
- [ ] Profile memory usage
- [ ] Check learning rate (often too high)
- [ ] Verify model is in train/eval mode correctly

### Experiment Tracking
```python
# Always log:
# - Hyperparameters
# - Training curves (loss, metrics)
# - Model checkpoints
# - Git commit hash
# - Hardware info
# - Random seeds
```

## Common Commands
```bash
# Profile PyTorch model
python -m torch.utils.bottleneck script.py

# TensorBoard
tensorboard --logdir=runs/

# GPU monitoring
nvidia-smi -l 1
watch -n 1 nvidia-smi

# Memory profiling
python -m memory_profiler script.py
```

## Red Flags
- Training loss stuck at same value -> learning rate issue
- Validation loss diverging -> overfitting, reduce model size or add regularization
- NaN losses -> gradient explosion, reduce LR or add clipping
- Memory errors -> reduce batch size, use gradient accumulation
