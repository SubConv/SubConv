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
                        <div class="subscription-row" v-for="item in subscriptions" :key="item.id">
                            <el-input v-model="item.value" placeholder="请粘贴订阅链接或分享链接" @paste="handleSubscriptionPaste($event, item.id, subscriptions)"></el-input>
                            <el-switch v-model="item.direct" active-text="强制直连"></el-switch>
                            <el-button @click="removeSubscription(item.id)" :disabled="subscriptions.length === 1">删除</el-button>
                        </div>
                        <el-button @click="addSubscription">添加订阅</el-button>
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
                    <div class="subscription-list standby-list" v-if="standby_switch">
                        <div class="subscription-row" v-for="item in standbySubscriptions" :key="item.id">
                            <el-input v-model="item.value" placeholder="请粘贴备用节点或备用订阅" @paste="handleSubscriptionPaste($event, item.id, standbySubscriptions)"></el-input>
                            <el-switch v-model="item.direct" active-text="强制直连"></el-switch>
                            <el-button @click="removeStandbySubscription(item.id)" :disabled="standbySubscriptions.length === 1">删除</el-button>
                        </div>
                        <el-button @click="addStandbySubscription">添加备用</el-button>
                    </div>
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

type SubscriptionInput = {
    id: number,
    value: string,
    direct: boolean
}

let nextSubscriptionId = 1
const createSubscriptionInput = (): SubscriptionInput => ({
    id: nextSubscriptionId++,
    value: '',
    direct: false
})

const subscriptions = ref<SubscriptionInput[]>([createSubscriptionInput()])
const standbySubscriptions = ref<SubscriptionInput[]>([createSubscriptionInput()])
const linkOutput = ref('')
const time = ref('')
const defaultTemplate = ref<string | null>(null)
const selectedTemplate = ref<string | null>(null)
const availableTemplates = ref<string[]>([])
const isLoadingRuntimeConfig = ref(true)
const hasRuntimeConfigError = ref(false)
const standby_switch = ref(false)
const proxy_switch = ref(true)

const splitSubscriptionInput = (value: string): string[] => value
    .split(/[|\n]/)
    .map((item) => item.trim())
    .filter((item) => item !== '')

const collectSubscriptions = (items: SubscriptionInput[]): string[] => items
    .flatMap((item) => splitSubscriptionInput(item.value))

const collectDirectSubscriptions = (items: SubscriptionInput[]): string[] => items
    .filter((item) => item.direct)
    .flatMap((item) => splitSubscriptionInput(item.value))

const isRemoteSubscription = (value: string) => (
    (value.startsWith('http://') || value.startsWith('https://')) && !value.startsWith('https://t.me/')
)

const hasInvalidDirectTarget = (items: string[]) => items.some((item) => !isRemoteSubscription(item))

const addSubscription = () => {
    subscriptions.value.push(createSubscriptionInput())
}

const removeSubscription = (id: number) => {
    if (subscriptions.value.length === 1) {
        return
    }
    subscriptions.value = subscriptions.value.filter((item) => item.id !== id)
}

const addStandbySubscription = () => {
    standbySubscriptions.value.push(createSubscriptionInput())
}

const removeStandbySubscription = (id: number) => {
    if (standbySubscriptions.value.length === 1) {
        return
    }
    standbySubscriptions.value = standbySubscriptions.value.filter((item) => item.id !== id)
}

const handleSubscriptionPaste = (event: ClipboardEvent, id: number, items: SubscriptionInput[]) => {
    const text = event.clipboardData?.getData('text') ?? ''
    const values = splitSubscriptionInput(text)
    if (values.length <= 1) {
        return
    }

    event.preventDefault()
    const index = items.findIndex((item) => item.id === id)
    if (index === -1) {
        return
    }

    items.splice(
        index,
        1,
        ...values.map((value) => ({
            ...createSubscriptionInput(),
            value,
            direct: items[index].direct
        }))
    )
}

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
const submitForm = () => {
    let result = window.location.protocol + "//" + window.location.host
    const primarySubscriptions = collectSubscriptions(subscriptions.value)
    const standbyValues = standby_switch.value ? collectSubscriptions(standbySubscriptions.value) : []
    const directSubscriptions = [
        ...collectDirectSubscriptions(subscriptions.value),
        ...(standby_switch.value ? collectDirectSubscriptions(standbySubscriptions.value) : [])
    ]

    if (primarySubscriptions.length > 0) {
        if (!selectedTemplate.value) {
            ElMessage({
                message: '模板配置加载失败，请刷新网页后重试',
                type: 'error'
            });
            linkOutput.value = ""
            return false;
        }
        if (hasInvalidDirectTarget(directSubscriptions)) {
            ElMessage({
                message: '强制直连仅支持 http/https 原始订阅链接',
                type: 'error'
            });
            linkOutput.value = ""
            return false;
        }
        result += "/sub?url=" + encodeURIComponent(primarySubscriptions.join('\n'));
        result += "&template=" + encodeURIComponent(selectedTemplate.value);
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
            if (standbyValues.length > 0) {
                result += "&urlstandby=" + encodeURIComponent(standbyValues.join('\n'));
            }
        }
        if (directSubscriptions.length > 0) {
            result += "&direct=" + encodeURIComponent(directSubscriptions.join('\n'));
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
    display: flex;
    flex-direction: column;
    gap: 12px;
    width: 100%;
}

.subscription-row {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
}

.subscription-row :deep(.el-input) {
    flex: 1;
}

.subscription-row :deep(.el-switch) {
    flex: 0 0 auto;
}

.standby-list {
    margin-top: 12px;
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
