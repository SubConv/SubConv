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

            <el-form label-position="labelPosition" label-width="100px" class="main">
                <el-form-item label="订阅">
                    <el-input type="textarea" v-model="linkInput" rows="5" resize="none"
                        placeholder="请粘贴订阅链接，或者分享链接，多个订阅链接请用逗号隔开"></el-input>
                </el-form-item>

                <el-form-item label="代理规则集">
                    <el-switch v-model="proxy_switch" active-text="关闭后将直接从GitHub获取规则集而非通过本服务器代理"></el-switch>
                </el-form-item>

                <el-form-item label="备用节点">
                    <el-switch v-model="standby_switch" active-text="备用节点只会出现在手动选择分组"></el-switch>
                    <el-input type="textarea" v-model="standby" rows="5" resize="none" v-if="standby_switch"
                        placeholder="请粘贴备用节点，多个备用节点请用逗号隔开"></el-input>
                </el-form-item>

                <el-form-item label="更新间隔">
                    <el-input v-model="time" style="width: 100px" placeholder=""></el-input>
                    秒，默认为1800
                </el-form-item>
                <el-form-item label="新订阅链接">
                    <el-input type="textarea" v-model="linkOutput" rows="2" resize="none"></el-input>
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="submitForm('ruleForm')">生成</el-button>
                    <el-button @click="copyForm('ruleForm')">复制</el-button>
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

<script>
export default {
    data() {
        return {
            linkInput: '',
            linkOutput: '',
            time: '',
            standby: '',
            standby_switch: false,
            proxy_switch: true
        };
    },
    methods: {
        submitForm() {
            let result = window.location.protocol + "//" + window.location.host
            if (this.linkInput !== "") {
                result += "/sub?url=" + encodeURIComponent(this.linkInput);
                if (this.time !== "") {
                    if (/^[1-9][0-9]*$/.test(this.time)) {
                        result += "&interval=" + this.time;
                    }
                    else {
                        this.$message({
                            message: '时间间隔必须为整数',
                            type: 'error'
                        });
                        return false;
                    }
                }
                if (this.standby_switch) {
                    if (this.standby !== "") {
                        result += "&urlstandby=" + encodeURIComponent(this.standby);
                    }
                }
                if (!this.proxy_switch) {
                    result += "&npr=1";
                }
            } else {
                this.$message({
                    message: '订阅链接不能为空',
                    type: 'error'
                });
                return false;
            }
            this.linkOutput = result
        },
        copyForm(formName) {
            navigator.clipboard.writeText(this.linkOutput);
            this.$message({
                message: '复制成功',
                type: 'success'
            })
        }
    }
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
