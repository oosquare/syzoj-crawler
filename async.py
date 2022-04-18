import asyncio
import hashlib
import re
import typing

import aiohttp
import bs4

host = "http://265ep45199.wicp.vip"
cookie = {}


def get_password_md5(password: str) -> str:
    password += "syzoj2_xxx"
    return hashlib.md5(password.encode("utf-8")).hexdigest()


async def init_cookie(username: str, password: str) -> typing.Dict[str, str]:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            host + "/api/login",
            data={
                "username": username,
                "password": get_password_md5(password),
            },
        ) as response:
            return response.cookies


async def get_problem_page_content(
    session: aiohttp.ClientSession, page_num: int
) -> str:
    async with session.get(
        host + "/problems", params={"page": str(page_num)}
    ) as response:
        return await response.text()


def check_problem_accepted(tag: bs4.Tag) -> typing.Tuple[str, str] | None:
    if tag.find("span", class_="status accepted") == None:
        return None

    problem_id = tag.b.string.strip()
    problem_name = (
        tag.find("a", style="vertical-align: middle; ")
        .contents[0]
        .strip()
        .replace("/", "-")
    )
    submission_url = tag.a["href"].strip()
    return f"{problem_id}-{problem_name}", host + submission_url


def get_accepted_problems(content: str) -> typing.Dict[str, str]:
    soup = bs4.BeautifulSoup(content, "html.parser")
    problem_table = soup.find("tbody")
    accepted_problems_dict = {}

    for row in problem_table.find_all("tr", recursive=False):
        res = check_problem_accepted(row)

        if res == None:
            continue

        accepted_problems_dict[res[0]] = res[1]

    return accepted_problems_dict


async def process_problem_page(
    session: aiohttp.ClientSession, page_num: int
) -> typing.Dict[str, str]:
    content = await get_problem_page_content(session, page_num)
    return get_accepted_problems(content)


async def get_problems(
    session: aiohttp.ClientSession, page_nums: typing.Iterable[int]
) -> typing.Dict[str, str]:
    problems_dict = {}
    result = await asyncio.gather(
        *[process_problem_page(session, num) for num in page_nums]
    )

    for page in result:
        problems_dict.update(page)

    return problems_dict


async def get_submission_content(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url) as response:
        return await response.text()


async def get_code_html(session: aiohttp.ClientSession, url: str) -> str:
    content = await get_submission_content(session, url)
    start = content.find('const unformattedCode = "') + len('const unformattedCode = "')
    end = content.find("\";", start, content.find('const formattedCode = "', start))
    return content[start:end].encode("utf-8").decode("unicode-escape")


async def get_code(session: aiohttp.ClientSession, url: str) -> str:
    code = await get_code_html(session, url)
    code = re.sub("</?[^>]+>", "", code, 0, re.M)
    code = re.sub("&lt;", "<", code, 0, re.M)
    code = re.sub("&gt;", ">", code, 0, re.M)
    code = re.sub("&amp;", "&", code, 0, re.M)
    code = re.sub("&quot;", '"', code, 0, re.M)
    code = re.sub("&apos;", "'", code, 0, re.M)
    code = re.sub("&#39;", "'", code, 0, re.M)
    return code


async def scrape_code(session: aiohttp.ClientSession, problem: str, url: str) -> None:
    try:
        code = await get_code(session, url)

        with open(problem + ".cpp", "w") as writer:
            writer.write(code)
    except Exception as e:
        print(f"Failed to scrape {problem} from {url}: {e}")


async def main() -> None:
    with open("passwd.txt") as f:
        username = f.readline().strip()
        password = f.readline().strip()

    cookie = await init_cookie(username, password)

    async with aiohttp.ClientSession(cookies=cookie) as session:
        if len(cookie) == 0:
            print("Failed to login.")
            return

        print("Succeeded to get cookie.")

        problems = await get_problems(session, range(1, 15))
        print(f"Succeeded to get the problem list. {len(problems)} problems in total.")

        await asyncio.gather(
            *[scrape_code(session, problem, url) for problem, url in problems.items()]
        )

        print("All tasks have finished.")


if __name__ == "__main__":
    asyncio.run(main())
