#!/usr/bin/env python3
"""把 lang-java/lessons 的 66 个 HTML 课件批量转换为 Markdown。

转换规则:
- title -> # 标题（正文首个 h1 跳过避免重复）
- div.meta -> blockquote 元信息
- h2/h3 -> ##/###
- p/li/strong/code -> markdown 对应
- details/summary 问答块 -> <details>/<summary> 保留折叠
- pre/code 代码块 -> ``` 围栏
- 去除 javaguide.cn 链接与 "JavaGuide《...》" 字样
- 去除内链 href 与样式表引用
"""
import html.parser
import os
import re


class HTMLToMD(html.parser.HTMLParser):
    def __init__(self, title):
        super().__init__()
        self.title = title
        self.out = []
        self.in_code = False
        self.code_buf = []
        self.in_pre = False
        self.details_depth = 0
        self.summary_depth = 0
        self.in_meta = 0
        self.meta_buf = []
        self.skip_depth = 0
        self.list_stack = []
        self.li_counter = 0
        self.h1_done = False

    # ---- 输出路由: details 内写 details 专用 buf 太复杂, 统一写 out,
    #      但 details 的文本需要缩进处理, 简单起见: details/summary 原样输出
    def emit(self, s):
        self.out.append(s)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            return
        if tag == "h1":
            self.block_break()
            if not self.h1_done:
                self.h1_done = True
                self.emit(f"# {self.title}\n")
            # 跳过正文 h1 内容
            self.skip_depth += 1
        elif tag == "h2":
            self.block_break()
            self.emit("## ")
        elif tag == "h3":
            self.block_break()
            self.emit("### ")
        elif tag == "h4":
            self.block_break()
            self.emit("#### ")
        elif tag == "p":
            self.block_break()
        elif tag == "strong" or tag == "b":
            self.emit("**")
        elif tag == "em" or tag == "i":
            self.emit("*")
        elif tag == "code" and not self.in_pre:
            self.emit("`")
        elif tag == "pre":
            self.in_pre = True
            self.in_code = True
            self.code_buf = []
        elif tag == "details":
            self.block_break()
            self.details_depth += 1
            self.emit("<details>\n\n")
        elif tag == "summary":
            self.summary_depth += 1
            self.emit("<summary>")
        elif tag == "ul":
            self.list_stack.append("ul")
            self.block_break()
        elif tag == "ol":
            self.list_stack.append("ol")
            self.li_counter = 0
            self.block_break()
        elif tag == "li":
            if self.list_stack and self.list_stack[-1] == "ol":
                self.li_counter += 1
                self.emit(f"{self.li_counter}. ")
            else:
                self.emit("- ")
        elif tag == "br":
            self.emit("  \n")
        elif tag == "div" and "meta" in a.get("class", ""):
            self.in_meta += 1
        elif tag == "div" and "label" in a.get("class", ""):
            self.emit("> ")
        elif tag == "a":
            href = a.get("href", "")
            if "javaguide" in href or href.startswith("./") or href.endswith(".css"):
                self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag == "h1":
            if self.skip_depth > 0:
                self.skip_depth -= 1
            self.emit("\n")
        elif tag in ("h2", "h3", "h4"):
            self.emit("\n")
        elif tag == "p":
            self.block_break()
        elif tag in ("strong", "b"):
            self.emit("**")
        elif tag in ("em", "i"):
            self.emit("*")
        elif tag == "code" and not self.in_pre:
            self.emit("`")
        elif tag == "pre":
            self.in_pre = False
            self.in_code = False
            code = "".join(self.code_buf).strip()
            self.block_break()
            self.emit("```\n" + code + "\n```\n")
        elif tag == "summary":
            self.summary_depth -= 1
            self.emit("</summary>\n\n")
        elif tag == "details":
            self.details_depth -= 1
            self.emit("\n</details>\n\n")
        elif tag in ("ul", "ol"):
            if self.list_stack:
                self.list_stack.pop()
            self.block_break()
        elif tag == "li":
            self.emit("\n")
        elif tag == "div" and self.in_meta > 0:
            self.in_meta -= 1
            if self.in_meta == 0:
                self.block_break()
                self.emit("> " + " · ".join(t.strip() for t in self.meta_buf if t.strip()) + "\n\n")
                self.meta_buf = []
        elif tag == "a":
            if self.skip_depth > 0:
                self.skip_depth -= 1

    def handle_data(self, data):
        if self.in_code:
            self.code_buf.append(data)
            return
        if self.skip_depth > 0:
            return
        if self.in_meta > 0:
            self.meta_buf.append(data)
            return
        # 去 javaguide 字样
        data = re.sub(r"JavaGuide《[^》]*》", "", data)
        data = re.sub(r"JavaGuide", "", data)
        data = re.sub(r"javaguide\.cn[^\s]*", "", data)
        # 折叠块内文本原样
        self.emit(data)

    def block_break(self):
        if self.out and not self.out[-1].endswith("\n\n"):
            self.emit("\n")

    def get_md(self):
        text = "".join(self.out)
        # 行首多余空格清理(代码块内除外 - 已转成围栏, 无碍)
        lines = []
        for ln in text.split("\n"):
            lines.append(ln.lstrip(" ") if not ln.startswith("```") else ln)
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = text.lstrip("\n")
        return text


def convert(path):
    with open(path, encoding="utf-8") as f:
        c = f.read()
    tm = re.search(r"<title>([^<]+)</title>", c)
    title = tm.group(1).strip() if tm else os.path.basename(path)
    c = re.sub(r"<title>[^<]*</title>", "", c)
    p = HTMLToMD(title)
    p.feed(c)
    return p.get_md()


def main():
    src = "/home/caoruixin/projects/lang-java/lessons"
    dst = "/home/caoruixin/桌面/ai-agent-interview-240/docs/02-语言八股/Java/课件"
    os.makedirs(dst, exist_ok=True)
    ok, fail = 0, []
    for fn in sorted(os.listdir(src)):
        if not fn.endswith(".html"):
            continue
        try:
            md = convert(os.path.join(src, fn))
            out = os.path.join(dst, fn.replace(".html", ".md"))
            with open(out, "w", encoding="utf-8") as f:
                f.write(md + "\n")
            ok += 1
        except Exception as e:
            fail.append((fn, str(e)))
    print(f"转换成功: {ok}, 失败: {len(fail)}")
    for fn, e in fail[:5]:
        print(f"  {fn}: {e}")
    # 验证
    jg = sum(1 for f in os.listdir(dst) if "javaguide" in open(os.path.join(dst, f), encoding="utf-8").read().lower())
    print(f"仍含 javaguide: {jg}")


if __name__ == "__main__":
    main()
