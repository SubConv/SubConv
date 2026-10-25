<template>
    <div>
        <el-card class="box-card">
            <div class="header">
                <a href="https://github.com/SubConv/SubConv">
                <span>
                    SubConv
                </span>
                <span>
                    <i class="fa-brands fa-github"></i>
                </span>
                </a>
            </div>

            <el-form label-position="right" label-width="100px" class="main">
                <el-form-item label="订阅">
                    <div class="subscription-list">
                        <div
                            v-for="(source, index) in subscriptionSources"
                            :key="source.id"
                            class="subscription-source"
                        >
                            <el-input
                                v-model="source.value"
                                class="subscription-input"
                                placeholder="请粘贴订阅链接或分享链接"
                            ></el-input>
                            <el-switch
                                v-model="source.forceDirect"
                                class="subscription-direct"
                                active-text="强制直连"
                            ></el-switch>
                            <el-button
                                :disabled="subscriptionSources.length === 1"
                                @click="removeSubscriptionSource(index)"
                            >
                                删除
                            </el-button>
                        </div>
                        <el-button @click="addSubscriptionSource">添加订阅</el-button>
                    </div>
                </el-form-item>

                <el-form-item label="模板">
                    <el-select
                        v-model="selectedTemplate"
                        style="width: 200px"
                        :disabled="!selectedTemplate"
                        :loading="isLoadingRuntimeConfig"
                        :placeholder="templatePlaceholder"
                    >
                        <el-option
                            v-for="template in templateOptions"
                            :key="template.value"
                            :label="template.label"
                            :value="template.value"
                        ></el-option>
                    </el-select>
                </el-form-item>

                <el-form-item label="代理规则集">
                    <el-switch v-model="proxy_switch" active-text="关闭后将直接从GitHub获取规则集而非通过本服务器代理"></el-switch>
                </el-form-item>

                <el-form-item label="备用节点">
                    <el-switch v-model="standby_switch" active-text="备用节点只会出现在手动选择分组"></el-switch>
                    <el-input type="textarea" v-model="standby" rows="5" resize="none" v-if="standby_switch"
                        placeholder="请粘贴备用节点，多个备用节点请换行或用|符号隔开"></el-input>
                </el-form-item>

                <el-form-item label="更新间隔">
                    <el-input v-model="time" style="width: 100px" placeholder=""></el-input>
                    秒，默认为1800
                </el-form-item>
                <el-form-item label="新订阅链接">
                    <el-input type="textarea" v-model="linkOutput" rows="2" resize="none"></el-input>
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="submitForm">生成</el-button>
                    <el-button @click="copyForm">复制</el-button>
                </el-form-item>
            </el-form>
        </el-card>
        <div class="footer">
            <div>
                <span>
                    <i class="fa fa-link" aria-hidden="true"></i>
                    API 后端项目:
                </span>
                <span>
                    <a href="https://github.com/SubConv/SubConv" target="_blank">
                        SubConv
                    </a>
                </span>
            </div>
            <div>
                <span>
                    <i class="fa fa-pencil" aria-hidden="true"></i>
                    UI designed by
                </span>
                <span>
                    <a href="https://github.com/musanico" target="_blank">@Musanico</a>
                </span>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
// init
import { computed, onMounted, ref } from 'vue'
import { ElButton, ElInput, ElForm, ElFormItem, ElCard, ElSwitch, ElMessage, ElSelect, ElOption } from 'element-plus'
import 'element-plus/es/components/button/style/css'
import 'element-plus/es/components/input/style/css'
import 'element-plus/es/components/form/style/css'
import 'element-plus/es/components/form-item/style/css'
import 'element-plus/es/components/card/style/css'
import 'element-plus/es/components/switch/style/css'
import 'element-plus/es/components/select/style/css'
import 'element-plus/es/components/option/style/css'
import 'element-plus/es/components/message/style/css'
type SubscriptionSource = {
    id: number
    value: string
    forceDirect: boolean
}

let subscriptionSourceId = 0

const createSubscriptionSource = (): SubscriptionSource => ({
    id: subscriptionSourceId += 1,
    value: '',
    forceDirect: false
})

const subscriptionSources = ref<SubscriptionSource[]>([createSubscriptionSource()])
const linkOutput = ref('')
const time = ref('')
const standby = ref('')
const defaultTemplate = ref<string | null>(null)
const selectedTemplate = ref<string | null>(null)
const availableTemplates = ref<string[]>([])
const isLoadingRuntimeConfig = ref(true)
const hasRuntimeConfigError = ref(false)
const standby_switch = ref(false)
const proxy_switch = ref(true)

const templateOptions = computed(() => [
    ...availableTemplates.value.map((templateName) => ({
        value: templateName,
        label: templateName
    }))
])

const templatePlaceholder = computed(() => {
    if (isLoadingRuntimeConfig.value) {
        return '模板配置加载中...'
    }
    if (hasRuntimeConfigError.value) {
        return '模板配置加载失败，请刷新网页后重试'
    }
    return '请选择模板'
})

const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms))

const initializeTemplateSelection = async () => {
    const maxAttempts = 3
    const retryDelayMs = [500, 1500]

    isLoadingRuntimeConfig.value = true
    hasRuntimeConfigError.value = false

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
        try {
            const response = await fetch('/config')
            if (!response.ok) {
                throw new Error(`Failed to load runtime config: ${response.status}`)
            }

            const runtimeConfig = await response.json() as {
                defaultTemplate?: string,
                availableTemplates?: string[]
            }

            const runtimeTemplates = Array.isArray(runtimeConfig.availableTemplates)
                ? runtimeConfig.availableTemplates
                : []

            if (runtimeTemplates.length === 0) {
                throw new Error('Runtime config did not include any available templates.')
            }

            availableTemplates.value = runtimeTemplates
            defaultTemplate.value = typeof runtimeConfig.defaultTemplate === 'string'
                ? runtimeConfig.defaultTemplate
                : null
            selectedTemplate.value = runtimeTemplates.includes(defaultTemplate.value ?? '')
                ? defaultTemplate.value
                : runtimeTemplates[0]
            isLoadingRuntimeConfig.value = false
            return
        }
        catch (error) {
            console.error(`Failed to initialize template selection from runtime config (attempt ${attempt}/${maxAttempts}).`, error)

            if (attempt < maxAttempts) {
                await sleep(retryDelayMs[attempt - 1])
                continue
            }

            availableTemplates.value = []
            defaultTemplate.value = null
            selectedTemplate.value = null
            hasRuntimeConfigError.value = true
            isLoadingRuntimeConfig.value = false
            ElMessage({
                message: '模板配置加载失败，请刷新网页后重试',
                type: 'error'
            })
        }
    }
}

onMounted(async () => {
    await initializeTemplateSelection()
})

// methods
const splitSourceInput = (source: string): string[] => source
    .split(/[|\n]/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0)

const isRemoteSubscriptionUrl = (source: string): boolean => {
    const trimmedSource = source.trim()
    return (trimmedSource.startsWith('http://') || trimmedSource.startsWith('https://'))
        && !trimmedSource.startsWith('https://t.me/')
}

const addSubscriptionSource = () => {
    subscriptionSources.value = [
        ...subscriptionSources.value,
        createSubscriptionSource()
    ]
}

const removeSubscriptionSource = (index: number) => {
    if (subscriptionSources.value.length === 1) {
        return
    }

    subscriptionSources.value = subscriptionSources.value.filter((_, currentIndex) => currentIndex !== index)
}

const submitForm = () => {
    let result = window.location.protocol + "//" + window.location.host
    const originalSources = subscriptionSources.value.flatMap((source) => splitSourceInput(source.value))
    const directSources = subscriptionSources.value.flatMap((source) => {
        if (!source.forceDirect) {
            return []
        }

        return splitSourceInput(source.value).filter(isRemoteSubscriptionUrl)
    })

    if (originalSources.length > 0) {
        if (!selectedTemplate.value) {
            ElMessage({
                message: '模板配置加载失败，请刷新网页后重试',
                type: 'error'
            });
            linkOutput.value = ""
            return false;
        }
        result += "/sub?url=" + encodeURIComponent(originalSources.join('\n'));
        result += "&template=" + encodeURIComponent(selectedTemplate.value);
        if (directSources.length > 0) {
            result += "&urldirect=" + encodeURIComponent(directSources.join('\n'));
        }
        if (time.value !== "") {
            if (/^[1-9][0-9]*$/.test(time.value)) {
                result += "&interval=" + time.value;
            }
            else {
                ElMessage({
                    message: '时间间隔必须为整数',
                    type: 'error'
                });
                linkOutput.value = ""
                return false;
            }
        }
        if (standby_switch.value) {
            if (standby.value !== "") {
                result += "&urlstandby=" + encodeURIComponent(standby.value);
            }
        }
        if (!proxy_switch.value) {
            result += "&npr=1";
        }
    } else {
        ElMessage({
            message: '订阅链接不能为空',
            type: 'error'
        });
        linkOutput.value = ""
        return false;
    }
    linkOutput.value = result
}

const copyForm = () => {
    navigator.clipboard.writeText(linkOutput.value);
    ElMessage({
        message: '复制成功',
        type: 'success'
    })
}

</script>

<style scoped>
.box-card {
    width: 1000px;
    height: auto;
    margin: 100px auto auto;
}

.main {
    margin-top: 60px;
}

.subscription-list {
    width: 100%;
}

.subscription-source {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
}

.subscription-input {
    flex: 1;
}

.subscription-direct {
    flex: 0 0 auto;
}

.header {
    display: block;
    margin-left: 33px;
    font-size: 20px;
    margin-top: 10px;
    margin-bottom: -30px;
}

.footer {
    text-align: center;
    margin-top: 20px;
}

a {
    color: black;
	text-decoration: none;
	position: relative;
}
footer a {
	color: #777777;
}
</style>
