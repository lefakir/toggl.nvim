# -*- coding: utf-8 -*-

import time
import neovim
from .api import TogglAPI
from requests.exceptions import ConnectionError


@neovim.plugin
class Toggl(object):

    def __init__(self, nvim):
        self.nvim = nvim
        self.api_token = nvim.eval("g:toggl_api_token")
        self.api = TogglAPI(self.api_token)
        self.http_rest_time = 60
        self.last_obtained = 0
        self.online = False

    @neovim.autocmd("VimEnter")
    def init_async(self):
        try:
            self.wid = self.api.workspaces()[0]["id"]
            self.projects = self.get_projects([])
        except ConnectionError:
            self.echo("No network, toggl.nvim is disabled.")
            self.online = False
        else:
            self.online = True

    @neovim.autocmd("CursorHold")
    def get_current(self):
        if not self.online:
            return
        now = time.time()
        if now - self.last_obtained < self.http_rest_time:
            return
        task = self.api.time_entries.current()
        self.nvim.vars["toggl_current"] = task
        self.last_obtained = now

    def echo(self, msg):
        self.nvim.command("echo '{}'".format(msg))

    @neovim.function("TogglAPIToken", sync=True)
    def api_token(self, args):
        return self.api_token

    @neovim.function("TogglGetProjects", sync=True)
    def get_projects(self, args):
        return self.api.workspaces.projects(self.wid)

    @neovim.function("TogglGetTags", sync=True)
    def get_tags(self, args):
        return self.api.workspaces.tags(self.wid)

    @neovim.command("TogglStart", range='', nargs="*")
    def start(self, args, range):
        projects = [arg[1:] for arg in args if arg[0] == "+"]
        if len(projects) > 1:
            raise RuntimeError("Multiple projects are specified.")
        if len(projects) == 1:
            name = projects[0]
        else:
            name = ""
        for p in self.projects:
            if p["name"] == name:
                pid = p["id"]
                break
        else:
            pid = 0

        tags = [arg[1:] for arg in args if arg[0] == "@"]
        desc = " ".join([arg for arg in args
                         if not arg.startswith(("+", "@"))])

        self.api.time_entries.start({
            "time_entry": {
                "description": desc,
                "pid": pid,
                "tags": tags,
                "created_with": "toggl.nvim",
            }
        })
        self.echo("Task Start: {}".format(desc))

    @neovim.command("TogglStop")
    def stop(self):
        current = self.api.time_entries.current()
        if current is None:
            self.echo("No task is running.")
            return
        self.api.time_entries.stop(current["id"])
        self.echo("Task Stop: {}".format(current["description"]))
