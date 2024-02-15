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
                    <el-input type="textarea" v-model="linkInput" rows="5" resize="none"
                        placeholder="请粘贴订阅链接，或者分享链接，多个订阅链接请换行或用|符号隔开"></el-input>
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
import { ref } from 'vue'
import { ElButton, ElInput, ElForm, ElFormItem, ElCard, ElSwitch, ElMessage } from 'element-plus'
import 'element-plus/es/components/button/style/css'
import 'element-plus/es/components/input/style/css'
import 'element-plus/es/components/form/style/css'
import 'element-plus/es/components/form-item/style/css'
import 'element-plus/es/components/card/style/css'
import 'element-plus/es/components/switch/style/css'
import 'element-plus/es/components/message/style/css'
const linkInput = ref('')
const linkOutput = ref('')
const time = ref('')
const standby = ref('')
const standby_switch = ref(false)
const proxy_switch = ref(true)

// methods
const submitForm = () => {
    let result = window.location.protocol + "//" + window.location.host
    if (linkInput.value !== "") {
        result += "/sub?url=" + encodeURIComponent(linkInput.value);
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
