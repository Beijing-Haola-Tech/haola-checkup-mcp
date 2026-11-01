#Requires -Version 5.1
<#
.SYNOPSIS
  好啦体检 MCP 的 PowerShell 客户端（Windows 兜底，不需要 Python）。

.DESCRIPTION
  和同目录的 haola.py 行为一致：同一套 MCP 握手、同一份能力白名单、同一个凭据文件。
  在没装 Python 的 Windows 上，用系统自带的 PowerShell 5.1 就能跑。

  子命令：
    ping      测连通性
    tools     列出当前可调用的工具
    call      调用工具：call <工具名> '<json>'
    login     弹出登录小窗，凭据存到 ~/.haola/token.json
    logout    清除本机凭据
    whoami    查看是否已登录
    quote     企业团检报价（仅企业版注册）

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\haola.ps1 ping
  powershell -ExecutionPolicy Bypass -File scripts\haola.ps1 call vendor_brands '{}'
  powershell -ExecutionPolicy Bypass -File scripts\haola.ps1 login
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)][string]$Command = "help",
    [Parameter(Position = 1)][string]$Arg1 = "",
    [Parameter(Position = 2)][string]$Arg2 = "",
    [int]$Timeout = 120,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch { }

# ---------------------------------------------------------------------------
# 能力边界：下面的值由构建脚本按 skill 覆写（见 build.mjs），运行时不改。
# ---------------------------------------------------------------------------
$MCP_URL = "https://ai.ihaola.com.cn/api/mcp/haola-pe"
$PROTOCOL_VERSION = "2025-06-18"
$TOKEN_ORIGIN = "https://ai.ihaola.com.cn"
$ISSUER = "https://ai.ihaola.com.cn"
$RESOURCE = "https://ai.ihaola.com.cn/api/mcp/haola-pe"
$SCOPE = "haola-pe"
$CLIENT_VERSION = "1.1.0"
$TOKEN_DIR = Join-Path $HOME ".haola"
$TOKEN_PATH = Join-Path $TOKEN_DIR "token.json"

# 以下六项由构建注入
$CLIENT_NAME = "好啦体检"
$SCOPE_NOTE = "免登录工具；本机登录后可使用全部个人体检工具"
$USE_LOCAL_TOKEN = $true
$ENABLE_CORPORATE_QUOTE = $true
$ANONYMOUS_TOOLS = @('plan_quotation','vendor_brands','vendor_list','knowledge_get','faq','corp_inquiry','corp_contact','help','progress_report')
$ALLOWED_TOOLS = @('vendor_list','vendor_brands','plan_quotation','knowledge_get','help','faq','progress_report','corp_inquiry','corp_contact','plan_recommend','order_list','order_detail','welfare_list','welfare_detail','cautions','contact_list','contact_get','contact_create','contact_update','contact_profile_get','contact_profile_save','reservation_book','reservation_cancel','reservation_modify','card_list')

# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------
try {
    [Console]::OutputEncoding = [Text.Encoding]::UTF8
    $OutputEncoding = [Text.Encoding]::UTF8
} catch { }

function Write-Err([string]$Message) { [Console]::Error.WriteLine($Message) }

function First-Line([string]$Text, [int]$Limit = 70) {
    if (-not $Text) { return "" }
    $cut = ($Text -replace "\s+", " ").Trim()
    $dot = $cut.IndexOf([char]0x3002)
    if ($dot -gt 0) { $cut = $cut.Substring(0, $dot) }
    if ($cut.Length -gt $Limit) { $cut = $cut.Substring(0, $Limit) + "…" }
    return $cut
}

# ---------------------------------------------------------------------------
# JSON
#   注意：Windows PowerShell 5.1 的 ConvertFrom-Json 对 key 大小写不敏感，
#   而本服务的工具 schema 里同时存在 contactid 与 contactId，
#   直接解析会报「重复键」。所以优先用 JavaScriptSerializer（区分大小写）。
# ---------------------------------------------------------------------------
$script:Json = $null
if ($PSVersionTable.PSVersion.Major -lt 6) {
    try {
        Add-Type -AssemblyName System.Web.Extensions
        $script:Json = New-Object System.Web.Script.Serialization.JavaScriptSerializer
        $script:Json.MaxJsonLength = 64MB
        $script:Json.RecursionLimit = 200
    } catch { $script:Json = $null }
}

function ConvertFrom-JsonSafe([string]$Text) {
    if (-not $Text) { return $null }
    if ($null -ne $script:Json) { return $script:Json.DeserializeObject($Text) }
    return ($Text | ConvertFrom-Json)
}

# 统一读取字段：兼容 IDictionary（5.1 走 JS 序列化器）与 PSObject（pwsh 走 ConvertFrom-Json）
function Get-Field($Obj, [string]$Name) {
    if ($null -eq $Obj) { return $null }
    if ($Obj -is [System.Collections.IDictionary]) {
        foreach ($k in $Obj.Keys) { if ([string]$k -ieq $Name) { return $Obj[$k] } }
        return $null
    }
    $p = $Obj.PSObject.Properties[$Name]
    if ($null -ne $p) { return $p.Value }
    return $null
}

# ---------------------------------------------------------------------------
# 凭据
# ---------------------------------------------------------------------------
function Get-Token {
    if (-not $USE_LOCAL_TOKEN) { return $null }
    if (-not (Test-Path $TOKEN_PATH)) { return $null }
    try { $t = ConvertFrom-JsonSafe ([IO.File]::ReadAllText($TOKEN_PATH, [Text.Encoding]::UTF8)) } catch { return $null }
    if ($null -eq $t) { return $null }
    $exp = Get-Field $t 'expires_at'
    if ($exp -and ([DateTimeOffset]::UtcNow.ToUnixTimeSeconds() -gt ([int64]$exp - 30))) { return $null }
    return $t
}

function Get-LoggedIn { return ($null -ne (Get-Token)) }

function Get-AuthHeaders {
    $t = Get-Token
    # 凭据只发给官方 origin：把地址换成别处时不附带 token
    if ($t -and $MCP_URL.StartsWith($TOKEN_ORIGIN + "/")) {
        return @{ "Authorization" = "Bearer " + (Get-Field $t 'access_token') }
    }
    return @{}
}

function Save-Token($Token) {
    if (-not (Test-Path $TOKEN_DIR)) { New-Item -ItemType Directory -Path $TOKEN_DIR -Force | Out-Null }
    $json = $Token | ConvertTo-Json -Depth 6
    [IO.File]::WriteAllText($TOKEN_PATH, $json, (New-Object Text.UTF8Encoding($false)))
}

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
Add-Type -AssemblyName System.Net.Http | Out-Null
$script:Http = New-Object System.Net.Http.HttpClient
$script:Http.Timeout = [TimeSpan]::FromSeconds(180)
$script:SessionId = $null
$script:NextId = 0
$script:Ready = $false
$script:ServerInfo = $null

function Invoke-Http {
    param(
        [string]$Url,
        [string]$Method = "POST",
        [hashtable]$Headers = @{},
        [byte[]]$Bytes = $null,
        [string]$ContentType = "application/json; charset=utf-8"
    )
    $req = New-Object System.Net.Http.HttpRequestMessage ([System.Net.Http.HttpMethod]::new($Method)), $Url
    if ($null -ne $Bytes) {
        $content = New-Object System.Net.Http.ByteArrayContent (, $Bytes)
        $content.Headers.TryAddWithoutValidation("Content-Type", $ContentType) | Out-Null
        $req.Content = $content
    }
    foreach ($k in $Headers.Keys) { $req.Headers.TryAddWithoutValidation($k, $Headers[$k]) | Out-Null }
    $resp = $script:Http.SendAsync($req).GetAwaiter().GetResult()
    $text = $resp.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    $sid = $null
    $vals = $null
    if ($resp.Headers.TryGetValues("mcp-session-id", [ref]$vals)) { $sid = ($vals | Select-Object -First 1) }
    return [pscustomobject]@{ Status = [int]$resp.StatusCode; Text = $text; Session = $sid }
}

function ConvertFrom-Sse([string]$Text) {
    if (-not $Text) { return $null }
    $trimmed = $Text.TrimStart()
    if ($trimmed.StartsWith("{")) { return (ConvertFrom-JsonSafe $trimmed) }
    $buf = ""
    foreach ($line in ($Text -split "`n")) {
        $l = $line.TrimEnd("`r")
        if ($l.StartsWith("data:")) { $buf += $l.Substring(5).TrimStart() }
    }
    if (-not $buf) { return $null }
    return (ConvertFrom-JsonSafe $buf)
}

function Invoke-Rpc([string]$Method, $Params) {
    $script:NextId++
    $payload = @{ jsonrpc = "2.0"; id = $script:NextId; method = $Method; params = $Params }
    $json = $payload | ConvertTo-Json -Depth 12 -Compress
    $headers = @{ "Accept" = "application/json, text/event-stream" }
    if ($script:SessionId) { $headers["mcp-session-id"] = $script:SessionId }
    $auth = Get-AuthHeaders
    foreach ($k in $auth.Keys) { $headers[$k] = $auth[$k] }

    $res = Invoke-Http -Url $MCP_URL -Headers $headers -Bytes ([Text.Encoding]::UTF8.GetBytes($json))
    if ($res.Session) { $script:SessionId = $res.Session }

    if ($res.Status -eq 401) { throw [System.UnauthorizedAccessException]::new("LOGIN_REQUIRED") }
    if ($res.Status -ge 400) {
        $msg = $res.Text
        try { $o = ConvertFrom-Sse $res.Text; $m = Get-Field (Get-Field $o 'error') 'message'; if ($m) { $msg = $m } } catch { }
        throw "HTTP $($res.Status)：$msg"
    }

    $obj = ConvertFrom-Sse $res.Text
    if ($null -eq $obj) { return $null }
    $err = Get-Field $obj 'error'
    if ($err) {
        $m = Get-Field $err 'message'
        if (-not $m) { $m = ($err | ConvertTo-Json -Compress) }
        throw "MCP 错误：$m"
    }
    return (Get-Field $obj 'result')
}

function Invoke-Notify([string]$Method, $Params) {
    $payload = @{ jsonrpc = "2.0"; method = $Method; params = $Params }
    $json = $payload | ConvertTo-Json -Depth 8 -Compress
    $headers = @{ "Accept" = "application/json, text/event-stream" }
    if ($script:SessionId) { $headers["mcp-session-id"] = $script:SessionId }
    $auth = Get-AuthHeaders
    foreach ($k in $auth.Keys) { $headers[$k] = $auth[$k] }
    $res = Invoke-Http -Url $MCP_URL -Headers $headers -Bytes ([Text.Encoding]::UTF8.GetBytes($json))
    if ($res.Session) { $script:SessionId = $res.Session }
}

function Connect-Mcp {
    if ($script:Ready) { return }
    $init = Invoke-Rpc "initialize" @{
        protocolVersion = $PROTOCOL_VERSION
        capabilities    = @{}
        clientInfo      = @{ name = "haola-checkup-ps"; version = $CLIENT_VERSION }
    }
    $script:ServerInfo = $init
    Invoke-Notify "notifications/initialized" @{}
    $script:Ready = $true
}

# ---------------------------------------------------------------------------
# 业务
# ---------------------------------------------------------------------------
function Invoke-Tool([string]$Name, $Arguments) {
    if ($ALLOWED_TOOLS -notcontains $Name) { throw "NOT_IN_SCOPE" }
    if (($ANONYMOUS_TOOLS -notcontains $Name) -and (-not (Get-LoggedIn))) { throw "LOGIN_REQUIRED" }

    $r = Invoke-Rpc "tools/call" @{ name = $Name; arguments = $Arguments }
    $text = ""
    foreach ($item in @(Get-Field $r 'content')) {
        if ((Get-Field $item 'type') -eq "text") { $text += (Get-Field $item 'text') }
    }
    if (Get-Field $r 'isError') {
        $m = $text
        try { $o = ConvertFrom-JsonSafe $text; if (Get-Field $o 'message') { $m = Get-Field $o 'message' } } catch { }
        throw "调用失败：$m"
    }
    if (-not $text) { return @{ raw = "" } }
    $payload = $null
    try { $payload = ConvertFrom-JsonSafe $text } catch { return @{ raw = $text } }
    $code = Get-Field $payload 'code'
    if ($code -and $code -ne 200) { throw ("业务错误 " + $code + "：" + (Get-Field $payload 'message')) }
    return $payload
}

function Get-FreePort {
    $l = New-Object System.Net.Sockets.TcpListener ([System.Net.IPAddress]::Loopback), 0
    $l.Start(); $p = $l.LocalEndpoint.Port; $l.Stop()
    return $p
}

function New-RandomBytes([int]$Length) {
    # .NET Framework 里 RandomNumberGenerator 没有静态 GetBytes(int)，只能用实例方法
    $bytes = New-Object byte[] $Length
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return , $bytes
}

function New-Pkce {
    $verifier = [Convert]::ToBase64String((New-RandomBytes 32)).Replace("+", "-").Replace("/", "_").TrimEnd("=")
    $sha = [Security.Cryptography.SHA256]::Create()
    $challenge = [Convert]::ToBase64String($sha.ComputeHash([Text.Encoding]::ASCII.GetBytes($verifier))).Replace("+", "-").Replace("/", "_").TrimEnd("=")
    return @{ verifier = $verifier; challenge = $challenge }
}

function Receive-Callback($Listener, [int]$DeadlineSeconds) {
    # 浏览器常会先请求 /favicon.ico，只处理一次会被它吃掉，所以循环到 /callback 为止
    $deadline = (Get-Date).AddSeconds($DeadlineSeconds)
    while ((Get-Date) -lt $deadline) {
        if (-not $Listener.Pending()) { Start-Sleep -Milliseconds 200; continue }
        $client = $Listener.AcceptTcpClient()
        try {
            $stream = $client.GetStream()
            $reader = New-Object System.IO.StreamReader ($stream, [Text.Encoding]::ASCII)
            $requestLine = $reader.ReadLine()
            if (-not $requestLine) { continue }
            $parts = $requestLine.Split(" ")
            $path = $parts[1]
            $ok = $path.StartsWith("/callback")
            $body = if ($ok) {
                "<!doctype html><meta charset='utf-8'><div style='font-family:system-ui;padding:48px;text-align:center'><h2>&#9989; 登录成功</h2><p>可以关掉这个窗口，回到对话里继续。</p></div>"
            } else {
                "<!doctype html><meta charset='utf-8'><div style='font-family:system-ui;padding:48px;text-align:center'>not found</div>"
            }
            $bodyBytes = [Text.Encoding]::UTF8.GetBytes($body)
            $head = "HTTP/1.1 " + $(if ($ok) { "200 OK" } else { "404 Not Found" }) + "`r`nContent-Type: text/html; charset=utf-8`r`nContent-Length: " + $bodyBytes.Length + "`r`nConnection: close`r`n`r`n"
            $headBytes = [Text.Encoding]::ASCII.GetBytes($head)
            $stream.Write($headBytes, 0, $headBytes.Length)
            $stream.Write($bodyBytes, 0, $bodyBytes.Length)
            $stream.Flush()
            if ($ok) { return $path }
        } finally { $client.Close() }
    }
    return $null
}

function Open-LoginWindow([string]$Url) {
    $candidates = @(
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
    )
    foreach ($exe in $candidates) {
        if ($exe -and (Test-Path $exe)) {
            try {
                Start-Process -FilePath $exe -ArgumentList "--app=$Url", "--window-size=520,840", "--window-position=200,80" | Out-Null
                return $true
            } catch { }
        }
    }
    try { Start-Process $Url | Out-Null; return $true } catch { return $false }
}

function Invoke-Login([int]$WaitSeconds, [bool]$OpenBrowser) {
    if (-not $USE_LOCAL_TOKEN) { Write-Err "本 skill 全程免登录，不需要登录。"; return 1 }

    $port = Get-FreePort
    $redirect = "http://127.0.0.1:$port/callback"
    $listener = New-Object System.Net.Sockets.TcpListener ([System.Net.IPAddress]::Loopback), $port
    $listener.Start()

    try {
        $regBody = @{
            client_name                = $CLIENT_NAME
            redirect_uris              = @($redirect)
            grant_types                = @("authorization_code", "refresh_token")
            response_types             = @("code")
            token_endpoint_auth_method = "none"
        } | ConvertTo-Json -Depth 6 -Compress
        $reg = Invoke-Http -Url "$ISSUER/api/auth/oauth/register" -Bytes ([Text.Encoding]::UTF8.GetBytes($regBody))
        if ($reg.Status -notin 200, 201) { throw "注册客户端失败：HTTP $($reg.Status) $($reg.Text)" }
        $regObj = ConvertFrom-JsonSafe $reg.Text
        $clientId = Get-Field $regObj 'client_id'
        if (-not $clientId) { throw "注册客户端失败：没有 client_id" }

        $pkce = New-Pkce
        $state = [Convert]::ToBase64String((New-RandomBytes 16)).Replace("+", "-").Replace("/", "_").TrimEnd("=")
        $query = @(
            "response_type=code"
            ("client_id=" + [uri]::EscapeDataString($clientId))
            ("redirect_uri=" + [uri]::EscapeDataString($redirect))
            ("scope=" + [uri]::EscapeDataString($SCOPE))
            ("state=" + [uri]::EscapeDataString($state))
            ("code_challenge=" + [uri]::EscapeDataString($pkce.challenge))
            "code_challenge_method=S256"
            ("resource=" + [uri]::EscapeDataString($RESOURCE))
        ) -join "&"
        $authUrl = "$ISSUER/api/auth/oauth/authorize?$query"

        Write-Host "请在浏览器里完成登录（这个页面是能用的授权页）："
        Write-Host $authUrl
        if ($OpenBrowser) { Open-LoginWindow $authUrl | Out-Null }

        $hit = Receive-Callback $listener $WaitSeconds
        if (-not $hit) { throw "没有拿到授权码：可能是超时，或授权页里没有完成登录。" }

        $qs = @{}
        $q = ($hit -split "\?", 2)
        if ($q.Length -gt 1) {
            foreach ($pair in $q[1].Split("&")) {
                $kv = $pair.Split("=", 2)
                if ($kv.Length -eq 2) { $qs[[uri]::UnescapeDataString($kv[0])] = [uri]::UnescapeDataString($kv[1]) }
            }
        }
        $code = $qs["code"]
        if (-not $code) { throw "没有拿到授权码。" }
        if ($qs["state"] -and $qs["state"] -ne $state) { throw "state 不匹配，可能被篡改，已中止。" }

        $form = @(
            "grant_type=authorization_code"
            ("code=" + [uri]::EscapeDataString($code))
            ("redirect_uri=" + [uri]::EscapeDataString($redirect))
            ("client_id=" + [uri]::EscapeDataString($clientId))
            ("code_verifier=" + [uri]::EscapeDataString($pkce.verifier))
            ("resource=" + [uri]::EscapeDataString($RESOURCE))
        ) -join "&"
        $tok = Invoke-Http -Url "$ISSUER/api/auth/oauth/token" -Bytes ([Text.Encoding]::UTF8.GetBytes($form)) -ContentType "application/x-www-form-urlencoded"
        if ($tok.Status -ne 200) { throw "换 token 失败：HTTP $($tok.Status) $($tok.Text)" }
        $tokObj = ConvertFrom-JsonSafe $tok.Text
        $access = Get-Field $tokObj 'access_token'
        if (-not $access) { throw "换 token 失败：响应里没有 access_token" }

        $expiresIn = Get-Field $tokObj 'expires_in'
        $tokenType = Get-Field $tokObj 'token_type'
        $saved = @{
            access_token  = $access
            refresh_token = Get-Field $tokObj 'refresh_token'
            token_type    = $(if ($tokenType) { $tokenType } else { "Bearer" })
            expires_at    = $(if ($expiresIn) { [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() + [int64]$expiresIn } else { $null })
            client_id     = $clientId
            obtained_at   = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        }
        Save-Token $saved

        Write-Host "登录成功，凭据已存到 $TOKEN_PATH"
        if ($saved.expires_at) {
            $left = [int64]$saved.expires_at - [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
            $span = if ($left -ge 86400) { "$([math]::Floor($left / 86400)) 天" } elseif ($left -ge 3600) { "$([math]::Floor($left / 3600)) 小时" } else { "$([math]::Max(1, [math]::Floor($left / 60))) 分钟" }
            Write-Host "  有效期约 $span，过期后重新跑一次 login 即可"
        }
        return 0
    } finally {
        try { $listener.Stop() } catch { }
    }
}

# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------
function Cmd-Ping {
    Connect-Mcp
    $s = Get-Field $script:ServerInfo 'serverInfo'
    Write-Host "连接成功：$MCP_URL"
    if ($script:SessionId) { Write-Host "  session      $($script:SessionId)" }
    if ($s) { Write-Host (("  server       " + (Get-Field $s 'name') + " " + (Get-Field $s 'version'))).TrimEnd() }
    $pv = Get-Field $script:ServerInfo 'protocolVersion'
    if ($pv) { Write-Host "  protocol     $pv" }
    if (-not $USE_LOCAL_TOKEN) {
        Write-Host "  模式         全程免登录（可调 $($ALLOWED_TOOLS.Count) 个企业工具）"
    } elseif (Get-LoggedIn) {
        Write-Host "  模式         已登录（本 skill 上限 $($ALLOWED_TOOLS.Count) 个工具）"
    } else {
        Write-Host "  模式         未登录（可调 $($ANONYMOUS_TOOLS.Count) 个免登录工具）"
    }
    return 0
}

function Cmd-Tools {
    Connect-Mcp
    $r = Invoke-Rpc "tools/list" @{}
    $shown = @()
    foreach ($t in @(Get-Field $r 'tools')) {
        $n = Get-Field $t 'name'
        if ($ALLOWED_TOOLS -notcontains $n) { continue }
        if ((-not (Get-LoggedIn)) -and ($ANONYMOUS_TOOLS -notcontains $n)) { continue }
        $shown += $t
    }
    $suffix = if ((Get-LoggedIn) -or (-not $USE_LOCAL_TOKEN)) { "" } else { "（未登录，需登录的暂不可调）" }
    Write-Host "当前可调用 $($shown.Count) 个工具$suffix"
    Write-Host ""
    foreach ($t in $shown) {
        $n = Get-Field $t 'name'
        Write-Host ("  " + $n.PadRight(24) + (First-Line (Get-Field $t 'description')))
    }
    if ((-not (Get-LoggedIn)) -and $USE_LOCAL_TOKEN) {
        Write-Host ""
        Write-Host "需要登录的工具：先跑 scripts\haola.ps1 login"
    }
    return 0
}

function Cmd-Call {
    $name = $Arg1
    if (-not $name) { Write-Err "用法：haola.ps1 call <工具名> '<json>'"; return 2 }
    if ($ALLOWED_TOOLS -notcontains $name) {
        Write-Err "``$name`` 不在本 skill 的调用范围内。"
        Write-Err ("本 skill 可调用的工具：" + (($ALLOWED_TOOLS | Sort-Object) -join "、"))
        return 5
    }
    if (($ANONYMOUS_TOOLS -notcontains $name) -and (-not (Get-LoggedIn))) {
        Write-Err "``$name`` 需要先登录。"
        if ($USE_LOCAL_TOKEN) { Write-Err "在这个目录下跑一次：scripts\haola.ps1 login" }
        return 3
    }
    $toolArgs = @{}
    if ($Arg2) { $toolArgs = ConvertFrom-JsonSafe $Arg2 }
    Connect-Mcp
    $out = Invoke-Tool $name $toolArgs
    # 直接写标准输出：脚本末尾用 exit (Cmd-xxx) 取退出码，走管道会被当成返回值吃掉
    [Console]::Out.WriteLine(($out | ConvertTo-Json -Depth 20))
    return 0
}

function Cmd-Login { return (Invoke-Login $Timeout (-not $NoBrowser)) }

function Cmd-Logout {
    if (Test-Path $TOKEN_PATH) { Remove-Item $TOKEN_PATH -Force; Write-Host "已清除本地凭据"; return 0 }
    Write-Host "本地没有凭据"
    return 0
}

function Cmd-Whoami {
    if (Get-LoggedIn) { Write-Host "已登录，凭据文件： $TOKEN_PATH"; return 0 }
    Write-Host "未登录"
    return 1
}

function Cmd-Quote {
    if (-not $ENABLE_CORPORATE_QUOTE) { Write-Err "本 skill 不做企业团检报价。"; return 5 }
    $budget = 0
    if ($Arg1) { [int]::TryParse($Arg1, [ref]$budget) | Out-Null }
    $concerns = $Arg2
    if ($budget -le 0 -or -not $concerns) { Write-Err '用法：haola.ps1 quote <人均预算> <健康关注>'; return 2 }
    Connect-Mcp
    $out = Invoke-Tool "plan_quotation" @{
        quotes = @(@{ tier = "员工档"; budget = $budget; healthConcerns = $concerns; populations = @("man", "lady", "girl") })
    }
    [Console]::Out.WriteLine(($out | ConvertTo-Json -Depth 20))
    return 0
}

function Show-Help {
    Write-Host "好啦体检 MCP 命令行（$SCOPE_NOTE）"
    Write-Host ""
    Write-Host "用法：powershell -ExecutionPolicy Bypass -File scripts\haola.ps1 <命令> [参数]"
    Write-Host ""
    $cmds = @(
        @{ n = "ping"; d = "测试连通性" },
        @{ n = "tools"; d = "列出可调用的工具" },
        @{ n = "call"; d = "调用工具：call <工具名> '<json>'" }
    )
    if ($USE_LOCAL_TOKEN) {
        $cmds += @{ n = "login"; d = "弹出登录小窗登录一次，之后自动带凭据" }
        $cmds += @{ n = "logout"; d = "清除本地凭据" }
        $cmds += @{ n = "whoami"; d = "查看是否已登录" }
    }
    if ($ENABLE_CORPORATE_QUOTE) {
        $cmds += @{ n = "quote"; d = "企业团检报价：quote <人均预算> <健康关注>" }
    }
    foreach ($c in $cmds) { Write-Host ("  " + $c.n.PadRight(10) + $c.d) }
    return 0
}

try {
    switch ($Command.ToLower()) {
        "ping" { exit (Cmd-Ping) }
        "tools" { exit (Cmd-Tools) }
        "call" { exit (Cmd-Call) }
        "login" { exit (Cmd-Login) }
        "logout" { exit (Cmd-Logout) }
        "whoami" { exit (Cmd-Whoami) }
        "quote" { exit (Cmd-Quote) }
        "help" { exit (Show-Help) }
        "-h" { exit (Show-Help) }
        "--help" { exit (Show-Help) }
        default { Write-Err "未知命令：$Command"; exit (Show-Help) }
    }
} catch [System.UnauthorizedAccessException] {
    Write-Err "需要登录后才能调用。在这个目录下跑一次：scripts\haola.ps1 login"
    exit 3
} catch {
    $msg = $_.Exception.Message
    if ($msg -eq "NOT_IN_SCOPE") { Write-Err "该工具不在本 skill 的调用范围内。"; exit 5 }
    if ($msg -eq "LOGIN_REQUIRED") { Write-Err "需要登录后才能调用。在这个目录下跑一次：scripts\haola.ps1 login"; exit 3 }
    Write-Err "失败：$msg"
    exit 1
}
