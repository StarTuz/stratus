use crate::quant::{bit_linear, BitLinear};
use candle_core::{Result, Tensor};
use candle_nn::{LayerNorm, Module};

#[derive(Debug, Clone)]
pub struct BitLlamaConfig {
    pub vocab_size: usize,
    pub hidden_size: usize,
    pub intermediate_size: usize,
    pub num_hidden_layers: usize,
    pub num_attention_heads: usize,
    pub num_key_value_heads: usize,
    pub rms_norm_eps: f64,
}

impl Default for BitLlamaConfig {
    fn default() -> Self {
        Self {
            vocab_size: 128256,
            hidden_size: 3072,
            intermediate_size: 8192,
            num_hidden_layers: 24,
            num_attention_heads: 24,
            num_key_value_heads: 8,
            rms_norm_eps: 1e-5,
        }
    }
}

#[derive(Debug, Clone)]
struct BitAttention {
    q_proj: BitLinear,
    k_proj: BitLinear,
    v_proj: BitLinear,
    o_proj: BitLinear,
    _num_heads: usize,
    _num_kv_heads: usize,
    _head_dim: usize,
}

impl BitAttention {
    fn load(vb: VarBuilder, config: &BitLlamaConfig) -> Result<Self> {
        let span = config.hidden_size;
        let q_proj = bit_linear(span, span, false, vb.device())?;
        let k_proj = bit_linear(span, span, false, vb.device())?;
        let v_proj = bit_linear(span, span, false, vb.device())?;
        let o_proj = bit_linear(span, span, false, vb.device())?;
        Ok(Self {
            q_proj,
            k_proj,
            v_proj,
            o_proj,
            _num_heads: config.num_attention_heads,
            _num_kv_heads: config.num_key_value_heads,
            _head_dim: config.hidden_size / config.num_attention_heads,
        })
    }

    fn forward(&self, x: &Tensor) -> Result<Tensor> {
        let q = self.q_proj.forward(x)?;
        let _k = self.k_proj.forward(x)?;
        let _v = self.v_proj.forward(x)?;
        self.o_proj.forward(&q)
    }
}

#[derive(Debug, Clone)]
struct BitMLP {
    gate_proj: BitLinear,
    up_proj: BitLinear,
    down_proj: BitLinear,
}

impl BitMLP {
    fn load(vb: VarBuilder, config: &BitLlamaConfig) -> Result<Self> {
        let h = config.hidden_size;
        let i = config.intermediate_size;
        let gate_proj = bit_linear(h, i, false, vb.device())?;
        let up_proj = bit_linear(h, i, false, vb.device())?;
        let down_proj = bit_linear(i, h, false, vb.device())?;
        Ok(Self {
            gate_proj,
            up_proj,
            down_proj,
        })
    }

    fn forward(&self, x: &Tensor) -> Result<Tensor> {
        let gate = self.gate_proj.forward(x)?;
        let up = self.up_proj.forward(x)?;
        let down = self.down_proj.forward(&(gate.silu()? * up)?)?;
        Ok(down)
    }
}

#[derive(Debug, Clone)]
struct BitDecoderLayer {
    self_attn: BitAttention,
    mlp: BitMLP,
    input_layernorm: LayerNorm,
    post_attention_layernorm: LayerNorm,
}

impl BitDecoderLayer {
    fn load(vb: VarBuilder, config: &BitLlamaConfig) -> Result<Self> {
        let self_attn = BitAttention::load(vb.pp("self_attn"), config)?;
        let mlp = BitMLP::load(vb.pp("mlp"), config)?;
        let input_layernorm = candle_nn::layer_norm(
            config.hidden_size,
            config.rms_norm_eps,
            vb.pp("input_layernorm"),
        )?;
        let post_attention_layernorm = candle_nn::layer_norm(
            config.hidden_size,
            config.rms_norm_eps,
            vb.pp("post_attention_layernorm"),
        )?;
        Ok(Self {
            self_attn,
            mlp,
            input_layernorm,
            post_attention_layernorm,
        })
    }

    fn forward(&self, x: &Tensor) -> Result<Tensor> {
        let residual = x;
        let x = self.input_layernorm.forward(x)?;
        let x = self.self_attn.forward(&x)?;
        let x = (x + residual)?;

        let residual = &x;
        let x = self.post_attention_layernorm.forward(&x)?;
        let x = self.mlp.forward(&x)?;
        let x = (x + residual)?;
        Ok(x)
    }
}

#[derive(Debug, Clone)]
pub struct BitLlama {
    embed_tokens: candle_nn::Embedding,
    layers: Vec<BitDecoderLayer>,
    norm: LayerNorm,
    lm_head: BitLinear,
}

use candle_nn::VarBuilder;

impl BitLlama {
    pub fn load(vb: VarBuilder, config: &BitLlamaConfig) -> Result<Self> {
        let embed_tokens = candle_nn::embedding(
            config.vocab_size,
            config.hidden_size,
            vb.pp("model.embed_tokens"),
        )?;
        let norm =
            candle_nn::layer_norm(config.hidden_size, config.rms_norm_eps, vb.pp("model.norm"))?;
        let lm_head = bit_linear(config.hidden_size, config.vocab_size, false, vb.device())?;

        let mut layers = Vec::with_capacity(config.num_hidden_layers);
        let vb_layers = vb.pp("model.layers");
        for i in 0..config.num_hidden_layers {
            layers.push(BitDecoderLayer::load(vb_layers.pp(i.to_string()), config)?);
        }

        Ok(Self {
            embed_tokens,
            layers,
            norm,
            lm_head,
        })
    }

    pub fn forward(&self, x: &Tensor) -> Result<Tensor> {
        let mut x = self.embed_tokens.forward(x)?;
        for layer in &self.layers {
            x = layer.forward(&x)?;
        }
        let x = self.norm.forward(&x)?;
        let logits = self.lm_head.forward(&x)?;
        Ok(logits)
    }
}
