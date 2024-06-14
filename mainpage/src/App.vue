<template>
    <div class="container">
        <el-card class="box-card">
            <div class="header">
                <a href="https://github.com/SubConv/SubConv" target="_blank">
                    <span>
                        SubConv
                    </span>
                    <span>
                        <i class="fa-brands fa-github"></i>
                    </span>
                </a>
                <el-button type="danger" @click="resetForm">重置</el-button>
            </div>

            <el-form label-position="top" label-width="100px" class="main">
                <el-form-item label="订阅链接">
                    <el-input type="textarea" v-model="form.linkInput" rows="5" resize="none"
                        placeholder="请粘贴订阅链接，或者分享链接，多个订阅链接请换行或用|符号隔开"></el-input>
                </el-form-item>

                <el-form-item label="高级设置">
                    <el-switch v-model="form.advanced_switch" active-text="开启后可以查看更多设置"></el-switch>
                </el-form-item>

                <template v-if="form.advanced_switch">
                    <el-form-item label="代理规则集">
                        <el-switch v-model="form.proxy_switch" active-text="关闭后将直接从GitHub获取规则集而非通过本服务器代理"></el-switch>
                    </el-form-item>

                    <el-form-item label="备用节点">
                        <el-switch v-model="form.standby_switch" active-text="备用节点只会出现在手动选择分组"></el-switch>
                        <el-input type="textarea" v-model="form.standby" rows="5" resize="none"
                            v-if="form.standby_switch" placeholder="请粘贴备用节点，多个备用节点请换行或用|符号隔开"></el-input>
                    </el-form-item>

                    <el-form-item label="更新间隔">
                        <el-input v-model="form.time" style="width: 100px" placeholder="1800"></el-input>
                        &nbsp;秒
                    </el-form-item>
                </template>

                <el-form-item label="新订阅链接">
                    <el-input type="textarea" v-model="form.linkOutput" rows="2" resize="none" readonly></el-input>
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="submitForm">生成</el-button>
                    <el-button @click="copyForm">复制</el-button>
                    <el-button :disabled="!form.linkOutput" @click="installClash"
                        class="clash-button">导入Clash</el-button>
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
    import { ref, onMounted } from 'vue'
    import { ElButton, ElInput, ElForm, ElFormItem, ElCard, ElSwitch, ElMessage } from 'element-plus'
    import 'element-plus/es/components/button/style/css'
    import 'element-plus/es/components/input/style/css'
    import 'element-plus/es/components/form/style/css'
    import 'element-plus/es/components/form-item/style/css'
    import 'element-plus/es/components/card/style/css'
    import 'element-plus/es/components/switch/style/css'
    import 'element-plus/es/components/message/style/css'

    const form = ref({
        linkInput: '',
        linkOutput: '',
        time: '',
        standby: '',
        standby_switch: false,
        proxy_switch: true,
        advanced_switch: false
    })

    const keys = Object.keys(form.value)

    onMounted(() => {
        keys.forEach(key => {
            if (localStorage.getItem(key)) {
                if (key.includes('switch') || key === 'advanced_switch') {
                    form.value[key] = localStorage.getItem(key) === 'true'
                } else {
                    form.value[key] = localStorage.getItem(key)
                }
            }
        })
    })

    const submitForm = () => {
        if (form.value.linkInput === "") {
            ElMessage({
                message: '订阅链接不能为空',
                type: 'error'
            })
            return
        }

        let result = `${window.location.protocol}//${window.location.host}/sub?url=${encodeURIComponent(form.value.linkInput)}`

        if (form.value.advanced_switch) {
            if (form.value.time === "0") {
                form.value.time = ''
            } else if (form.value.time !== "" && /^[1-9][0-9]*$/.test(form.value.time)) {
                result += `&interval=${form.value.time}`
            } else if (form.value.time !== "") {
                ElMessage({
                    message: '更新间隔必须为整数',
                    type: 'error'
                })
                form.value.time = ''
                return
            }
            if (form.value.standby_switch && form.value.standby !== "") {
                result += `&urlstandby=${encodeURIComponent(form.value.standby)}`
            }
            if (!form.value.proxy_switch) {
                result += "&npr=1"
            }
        }

        form.value.linkOutput = result
        copyForm()
        saveToLocalStorage()
    }

    const copyForm = () => {
        navigator.clipboard.writeText(form.value.linkOutput)
        ElMessage({
            message: '复制成功',
            type: 'success'
        })
    }

    const installClash = () => {
        if (form.value.linkOutput === "") {
            submitForm()
        }
        const clashURL = `clash://install-config?url=${encodeURIComponent(form.value.linkOutput)}`
        window.location.href = clashURL
        ElMessage({
            message: '正在启动Clash...',
            type: 'warning',
            duration: 5000
        })
    }

    const resetForm = () => {
        keys.forEach(key => {
            form.value[key] = key === 'proxy_switch' ? true : key.includes('switch') || key === 'advanced_switch' ? false : ''
            localStorage.removeItem(key)
        })

        ElMessage({
            message: '已重置',
            type: 'success'
        })
    }

    const saveToLocalStorage = () => {
        keys.forEach(key => localStorage.setItem(key, form.value[key]))
    }
</script>

<style scoped>
    .container {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 20px;
    }

    .box-card {
        width: 90%;
        max-width: 1000px;
        margin-top: 20px;
    }

    .main {
        margin-top: 20px;
    }

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: -10px;
    }

    .footer {
        text-align: center;
        margin-top: 20px;
    }

    .footer div {
        margin-top: 4px;
    }

    a {
        color: black;
        text-decoration: none;
    }

    .footer a {
        color: #777777;
    }

    .clash-button {
        background: linear-gradient(to right bottom, #ed87b6, #8f83f7);
        border: none;
        color: white;
    }

    .clash-button:hover {
        background: linear-gradient(to right bottom, #f4a6c0, #a29bf8);
    }

    .clash-button:disabled {
        color: white;
        background: #cccccc;
        cursor: not-allowed;
    }

    @media (max-width: 768px) {
        .container {
            padding: 0;
        }

        .box-card {
            width: 100%;
            margin-top: 0;
        }
    }
</style>
