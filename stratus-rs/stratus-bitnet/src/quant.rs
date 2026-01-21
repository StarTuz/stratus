use candle_core::{Device, Result, Tensor};
use candle_nn::Module;

/// BitLinear layer for BitNet b1.58
///
/// This layer implements the ternary quantization logic:
/// - Weights are quantized to {-1, 0, 1}
/// - Activations are quantized to 8-bit (absmax scaling)
/// - Efficient matrix multiplication is used for the ternary weights
#[derive(Debug, Clone)]
pub struct BitLinear {
    weight: Tensor,
    bias: Option<Tensor>,
    scale: f32, // Learned or calculated scale for weights
}

impl BitLinear {
    pub fn new(weight: Tensor, bias: Option<Tensor>) -> Self {
        // In a real implementation, we'd calculate the scale from the weights
        // Here we assume it's provided or normalized to 1.0 for now
        Self {
            weight,
            bias,
            scale: 1.0,
        }
    }

    /// Quantize activations to 8-bit
    fn quantize_activations(&self, x: &Tensor) -> Result<Tensor> {
        // x_q = RoundClip(x * 127 / max(abs(x)), -128, 127)
        let abs_max = x.abs()?.flatten_all()?.max(0)?;
        let scale = (abs_max.to_scalar::<f32>()? / 127.0).max(1e-5);

        // Simple scaling for now, assuming fp32 operations but simulating quantization effect
        // or actually casting to i8 if candle-core supported it efficiently in matmul
        (x / (scale as f64))?.round()?.clamp(-128.0, 127.0)
    }
}

impl Module for BitLinear {
    fn forward(&self, x: &Tensor) -> Result<Tensor> {
        let x_q = self.quantize_activations(x)?;

        // Quantize weights to ternary {-1, 0, 1}
        // w_q = Sign(w - mean(w))
        let mean = self.weight.mean_all()?;
        let centered_w = self.weight.broadcast_sub(&mean)?;
        let weight_q = centered_w.sign()?;

        // y = matmul(x_q, weight_q^T) * scale
        let mut y = x_q.matmul(&weight_q.t()?)?;

        if let Some(ref bias) = self.bias {
            y = y.broadcast_add(bias)?;
        }

        // Re-scale back
        y * (self.scale as f64)
    }
}

pub fn bit_linear(in_dim: usize, out_dim: usize, bias: bool, device: &Device) -> Result<BitLinear> {
    let weight = Tensor::zeros((out_dim, in_dim), candle_core::DType::F32, device)?;
    let bias = if bias {
        Some(Tensor::zeros(out_dim, candle_core::DType::F32, device)?)
    } else {
        None
    };
    Ok(BitLinear::new(weight, bias))
}

#[cfg(test)]
mod tests {
    use super::*;
    use candle_core::{Device, Tensor};

    #[test]
    fn test_ternary_logic() -> candle_core::Result<()> {
        let device = Device::Cpu;
        // Weights: [1, 0, -1]
        let weight = Tensor::new(&[[1.0f32, 0.0, -1.0]], &device)?;
        let mut bl = BitLinear::new(weight, None);
        bl.scale = 1.0;

        // Input: [10, 10, 10]
        let input = Tensor::new(&[[10.0f32, 10.0, 10.0]], &device)?;
        let output = bl.forward(&input)?;

        // Sign(w - mean) where mean = 0
        // weight_q = [1, 0, -1]
        // dot([10, 10, 10], [1, 0, -1]) = 10 + 0 - 10 = 0

        let out_vals: Vec<Vec<f32>> = output.to_vec2()?;
        assert!(out_vals[0][0].abs() < 1e-5);
        Ok(())
    }
}
