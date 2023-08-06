import os
from email.mime.multipart import MIMEMultipart
import requests
import datetime
import smtplib
from email.mime.text import MIMEText
from email.header import Header


def get_repo_file_changes(file_name, token):
    result = {}
    yesterday = datetime.datetime.now() - datetime.timedelta(1)
    yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_unix_time = int(yesterday.timestamp())

    with open(file_name, 'r') as f:
        repos = f.readlines()
    for repo in repos:
        if repo.strip() and repo.startswith('#') is False:
            owner, name = repo.strip().split('/')
            url = f"https://api.github.com/repos/{owner}/{name}/branches"
            headers = {'Authorization': f'token {token}'}
            r = requests.get(url, headers=headers)
            branches_data = r.json()
    
            for branch_data in branches_data:
                branch_name = branch_data['name']
                last_commit_url = f"https://api.github.com/repos/{owner}/{name}/branches/{branch_name}"
                r = requests.get(last_commit_url, headers=headers)
                last_commit = r.json()['commit']
    
                # 修改这里获取时间戳的方式
                last_commit_time_str = last_commit['commit']['committer']['date']
                last_commit_time = datetime.datetime.strptime(last_commit_time_str, '%Y-%m-%dT%H:%M:%SZ')
                last_commit_unix_time = int(last_commit_time.timestamp())
                # print(last_commit_time_str,last_commit_time,last_commit_unix_time)
                # 2023-03-08T06:15:55Z 2023-03-08 06:15:55 1678227355
                # 2023-02-02T05:31:34Z 2023-02-02 05:31:34 1675287094
                if last_commit_unix_time >= yesterday_unix_time:
                    last_commit_sha = last_commit['sha']
                    # https://api.github.com/repos/xx/xx/commits/e06b4b05e19e95dcf845a4e5499711e210ffdb52
                    commit_url = f"https://api.github.com/repos/{owner}/{name}/commits/{last_commit_sha}"
                    r = requests.get(commit_url, headers=headers)
                    commit_data = r.json()
                    file_changes = commit_data['files']
                    # print(file_changes)
                    for file_change in file_changes:
                        result.setdefault(f"{owner}/{name}/tree/{branch_name}", []).append(
                            file_change['filename'] + '\t' + file_change['status'])
                        # 设置字典键和值
                # print(result)
    return result


def send_email(subject, to_addr, text, smtp_server, smtp_port, from_addr, password):
    # msg = MIMEText(text, 'plain', 'utf-8')
    msg = MIMEMultipart()
    html = MIMEText(text, "html")
    msg.attach(html)
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = Header(from_addr)
    msg['To'] = to_addr

    smtp_server = smtplib.SMTP(smtp_server, int(smtp_port))
    smtp_server.starttls()
    smtp_server.login(from_addr, password)
    smtp_server.sendmail(from_addr, [to_addr], msg.as_string())
    smtp_server.quit()


if __name__ == '__main__':
    file_name = 'projects.txt'
    # token = '{{ secrets.token }}'
    # # 修改为您要使用的邮箱地址和SMTP服务器信息，以及您的邮箱密码
    # smtp_server = '{{ secrets.smtp_server }}'
    # smtp_port = '{{ secrets.smtp_port }}'
    # from_addr = '{{ secrets.from_addr }}'
    # password = '{{ secrets.password }}'
    # to_addr = '{{ secrets.to_addr }}'
    token = os.getenv('GITHUB_TOKEN')
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = os.getenv('SMTP_PORT')
    from_addr = os.getenv('FROM_ADDR')
    password = os.getenv('EMAIL_PASSWORD')
    to_addr = os.getenv('TO_ADDR')

    file_changes = get_repo_file_changes(file_name, token)
    # print(file_changes)
    text = ''
    for repo, changes in file_changes.items():
        # repo = komomon/komo/tree/beta
        branch_link = f'<h3><a href="https://github.com/{repo}">{repo}</a>有以下文件更新:</h3>'
        text += f"{branch_link}"
        for change in changes:
            text += f"{change}<br>"
    print(text)
    # exit()
    if text.strip() == '':
        print("No changes detected.")
    else:
        send_email('Github monitor project file changes', to_addr, text, smtp_server, smtp_port, from_addr, password)
        print("Email sent.")
