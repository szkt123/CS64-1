<template>
  <div>
    <el-card>
      <template #header><b>Training Parameters</b></template>
      <el-form :model="form" label-width="180px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="Train JSONL"><el-input v-model="form.train_jsonl" placeholder="For example: ./data/splits/train.jsonl" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="Val JSONL"><el-input v-model="form.val_jsonl" placeholder="For example: ./data/splits/val.jsonl" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="Output Dir"><el-input v-model="form.output_dir" placeholder="For example: ./runs/run1" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Batch Size"><el-input-number v-model="form.batch_size" :min="1" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Epochs"><el-input-number v-model="form.epochs" :min="1" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Learning Rate"><el-input-number v-model="form.lr" :step="0.00001" :precision="6" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Weight Decay"><el-input-number v-model="form.weight_decay" :step="0.0001" :precision="6" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Dropout"><el-input-number v-model="form.dropout" :step="0.05" :precision="2" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Proj Dim"><el-input-number v-model="form.proj_dim" :min="64" :step="64" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Max Text Length"><el-input-number v-model="form.max_text_length" :min="32" :step="32" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Ranking Weight"><el-input-number v-model="form.ranking_weight" :step="0.05" :precision="2" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Num Workers"><el-input-number v-model="form.num_workers" :min="0" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Log Every"><el-input-number v-model="form.log_every" :min="1" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Emit Every"><el-input-number v-model="form.emit_every" :min="1" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Cross-Attn Heads"><el-input-number v-model="form.cross_attention_heads" :min="1" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Cross-Attn Layers"><el-input-number v-model="form.cross_attention_layers" :min="1" /></el-form-item></el-col>
        </el-row>
        <el-space wrap class="option-row">
          <el-tooltip
            v-for="item in trainingOptions"
            :key="item.key"
            :content="item.tip"
            placement="top"
            effect="light"
            popper-class="training-option-tooltip"
          >
            <el-checkbox v-model="form[item.key]" class="training-option">
              <span class="option-label">{{ item.label }}</span>
              <el-icon class="option-help"><QuestionFilled /></el-icon>
            </el-checkbox>
          </el-tooltip>
        </el-space>
        <div style="margin-top:16px">
          <el-button type="primary" :loading="loading" @click="startTraining">Start training</el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { QuestionFilled } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'

const router = useRouter()
const loading = ref(false)
const form = reactive({
  train_jsonl: './data/splits/train.jsonl',
  val_jsonl: './data/splits/val.jsonl',
  output_dir: './runs/run1',
  batch_size: 4,
  epochs: 5,
  lr: 0.00002,
  weight_decay: 0.0001,
  dropout: 0.1,
  proj_dim: 256,
  max_text_length: 256,
  ranking_weight: 0.2,
  verify_images: true,
  include_weak_labels: false,
  use_ranking_loss: true,
  freeze_text_encoder: false,
  freeze_image_encoder: false,
  save_every_epoch: false,
  num_workers: 0,
  log_every: 10,
  emit_every: 1,
  cross_attention_heads: 4,
  cross_attention_layers: 1,
  use_bidirectional_cross_attention: false,
  text_model_name: 'allenai/scibert_scivocab_uncased',
  image_model_name: 'openai/clip-vit-base-patch32',
  seed: 42,
})

const trainingOptions = [
  {
    key: 'verify_images',
    label: 'verify_images',
    tip: 'Check image paths before training.',
  },
  {
    key: 'include_weak_labels',
    label: 'include_weak_labels',
    tip: 'Use low-confidence labels as extra data.',
  },
  {
    key: 'use_ranking_loss',
    label: 'use_ranking_loss',
    tip: 'Learn relative figure-quality order.',
  },
  {
    key: 'freeze_text_encoder',
    label: 'freeze_text_encoder',
    tip: 'Keep the text encoder unchanged.',
  },
  {
    key: 'freeze_image_encoder',
    label: 'freeze_image_encoder',
    tip: 'Keep the image encoder unchanged.',
  },
  {
    key: 'save_every_epoch',
    label: 'save_every_epoch',
    tip: 'Save a checkpoint after each epoch.',
  },
  {
    key: 'use_bidirectional_cross_attention',
    label: 'bidirectional_cross_attn',
    tip: 'Let text and image attend to each other.',
  },
]

const startTraining = async () => {
  loading.value = true
  try {
    const { data } = await api.post('/train/start', form)
    ElMessage.success('Training has begun')
    router.push(`/monitor/${data.run_id}`)
  } catch (err) {
    const detail = err?.response?.data?.detail || 'Startup failed'
    ElMessage.error(String(detail))
  } finally {
    loading.value = false
  }
}
</script>


<style scoped>
.option-row {
  align-items: center;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fafafa;
}

.training-option {
  margin-right: 8px;
}

.option-label {
  font-size: 13px;
}

.option-help {
  margin-left: 4px;
  color: #909399;
  font-size: 13px;
  vertical-align: -2px;
}

.training-option:hover .option-label,
.training-option:hover .option-help {
  color: #409eff;
}

:global(.training-option-tooltip) {
  max-width: 220px;
  line-height: 1.4;
  font-size: 12px;
}
</style>
