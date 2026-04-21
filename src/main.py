from cProfile import label

from flet import control

import flet as ft
ft.context.disable_auto_update()
from selectolax.lexbor import LexborHTMLParser
import asyncio
import os
import sys
import hashlib
from dataclasses import field
from typing import Callable

application_dir = os.path.dirname(sys.executable)
browsers_path = os.path.join(application_dir, "ms-playwright")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path

from services.preview import PreviewGenerator

PREVIEW_CACHE_DIR = PreviewGenerator().get_app_data_dir()

url_list = []
@ft.control
class Bookmark(ft.Column):
    page_name: str = ""
    link: str = ""
    node = None
    callback_show_preview = None
    on_bookmark_delete: Callable[["Bookmark"], None] = field(default=lambda task: None)

    def init(self):
        self.controls = [
            ft.Text(
                value=self.page_name,
                color="black",
                size=14,
                selectable=True,
                enable_interactive_selection=True
            ),
            ft.Row(
                controls=[
                    ft.Button(
                        content="Preview",
                        on_hover=lambda e, url=self.link: self.callback_show_preview(e, url),
                        bgcolor="white",
                        color='#242b40'
                    ),
                    ft.Button(
                        content="Remove",
                        on_click=self.del_button_clicked,
                        bgcolor="white",
                        color='#242b40'
                    ),
                ]
            ),
        ]

    def del_button_clicked(self):
        self.on_bookmark_delete(self)


@ft.control
class BookmarkApp(ft.Column):
    # Application's root control is a Column containing all other controls
    def init(self):
        self.preview_gen = PreviewGenerator()
        self.bookmarks = ft.Column()
        self.folders_column = ft.Column()
        self.selected_folder = None
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.input_field = ft.TextField(
            label="Enter the contents of your bookmarks.html file",
            min_lines=1,
            max_lines=5,
            border=ft.InputBorder.NONE,
            filled=True,
            expand=True,
        )
        self.start_button = ft.Button(
            content="Start",
            on_click=self.start_button_clicked,
            bgcolor="white",
            color='#242b40'
        )
        self.save_button = ft.Button(
            content="Save",
            on_click=self.save_button_clicked,
            bgcolor="blue",
            color='#242b40'
        )
        self.progressbar = ft.ProgressBar(width=200, value=0, visible=False)
        self.wizard_icon = ft.Icon(
            ft.CupertinoIcons.WAND_STARS_INVERSE,
            color='#242b40',
            size=40)
        self.complete_message = ft.Text(
            size=18,
            weight=ft.FontWeight.BOLD,
            value="˙✦⋆˚✧｡⊹° Done! °⊹｡✧˚⋆✦˙",
            color='#242b40'
        )
        self.complete = ft.Stack(
            alignment=ft.Alignment.CENTER,
            visible=False,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self.wizard_icon,
                        ],
                    ),

                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self.complete_message,
                        ],
                    ),
                ]
        )
        self.saved_message = ft.Text(
            size=18,
            weight=ft.FontWeight.BOLD,
            value="˙✦⋆˚✧｡⊹° Saved! °⊹｡✧˚⋆✦˙",
            color='#242b40'
        )
        self.saved = ft.Stack(
            alignment=ft.Alignment.CENTER,
            visible=False,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self.wizard_icon,
                    ],
                ),

                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self.saved_message,
                    ],
                ),
            ]
        )
        self.controls = [
            self.input_field,
            self.start_button,
            self.save_button,
            self.progressbar,
            self.complete,
            self.saved,
            self.bookmarks,
        ]

        # -------------------------------
        # Preview section
        # -------------------------------

        self.preview_image = ft.Image(src="", width=300, height=500)
        self.preview_container = ft.Container(
            right=20,
            top=20,
            width=300,
            height=500,
            content=self.preview_image,
            border_radius=5,
            border=ft.Border.all(),
            padding=5,
            visible=False,
        )

    def did_mount(self):
        self.page.overlay.append(self.preview_container)
        self.page.run_task(self.preview_gen.init_browser)

    def show_preview(self, e, url: str):
        global url_list

        if e.data:

            filename = hashlib.md5(url.encode()).hexdigest() + ".png"
            file_path = os.path.join(PREVIEW_CACHE_DIR, filename)
            if os.path.exists(file_path):
                self.preview_image.src = file_path
                self.preview_container.visible = True
                self.page.update()
                return

            # To avoid multiple hovers over the same button at the same time
            if url in url_list:
                self.preview_image.src = "previews/loading.png"
                self.preview_container.visible = True
                self.page.update()
                return

            print(f"Loading preview for {url}")
            try:
                self.preview_image.src = "previews/loading.png"
                self.preview_container.visible = True
                self.page.update()
                url_list.append(url)
                self.page.run_task(self.load_preview_async, url)
            except Exception as e:
                print(e)
        else:
            print(f"Hiding preview")
            self.preview_container.visible = False
            self.page.update()

    async def load_preview_async(self, url: str):
        global url_list
        try:
            path = await self.preview_gen.get_cached_preview(url)

            if path:
                self.preview_image.src = path
                url_list.remove(url)
        except asyncio.CancelledError:
            print(f"Preview load canceled for {url}")
        except Exception as e:
            print(f"Error while loading preview: {e}")
            self.preview_image.src = ""
        finally:
            self.page.update()


    # -------------------------------
    # Parser section
    # -------------------------------

    def parse_dl(self, dl, level=0):
        child = dl.child

        while child:
            if child.tag == 'dt':
                inner = child.child

                while inner:
                    # 🔗 Link
                    if inner.tag == 'a':
                        name = inner.text()
                        url = inner.attributes.get('href')
                        self.result += "  " * level + f"{name}     {url}\n"

                        # Build bookmarks column
                        bookmark = Bookmark(
                            page_name=inner.text(),
                            link=inner.attributes.get('href'),
                            on_bookmark_delete=self.bookmark_delete
                        )

                        bookmark.node = child  # <DT>
                        bookmark.callback_show_preview = self.show_preview
                        self.bookmarks.controls.append(bookmark)

                    # 📁 Folder
                    elif inner.tag == 'h3':
                        folder_name = inner.text()

                        self.result += "  " * level + f"[{folder_name}]\n"

                        self.bookmarks.controls.append(
                            ft.Text(
                                value=folder_name,
                                color="white",
                                size=16,
                                weight=ft.FontWeight.W_700
                            )
                        )

                        # Build folder column
                        base_width = 240
                        indent_per_level = 20
                        btn_width = max(40, base_width - indent_per_level * level)

                        folder_button = ft.Button(
                            content=ft.Row(controls=[ft.Text(folder_name)]),
                            width=btn_width,
                            bgcolor="grey",
                            color="white",
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=10),
                                animation_duration=200,
                                side = {
                                    ft.ControlState.DEFAULT: ft.BorderSide(
                                        0
                                    ),
                                    ft.ControlState.HOVERED: ft.BorderSide(
                                        3, color=ft.Colors.BLUE_600
                                    ),
                                },
                            )
                        )

                        folder_button.on_click = lambda e, node=inner, btn=folder_button: self.select_folder(
                            e, node, btn)

                        self.folders_column.controls.append(folder_button)

                        # Inner DL (always after H3)
                        sub_dl = inner.next
                        while sub_dl and sub_dl.tag != 'dl':
                            sub_dl = sub_dl.next

                        if sub_dl:
                            self.parse_dl(sub_dl, level + 1)

                    inner = inner.next

            child = child.next

    def select_folder(self, e, node, btn):
        # Remove old selected border
        if self.selected_folder:
            self.selected_folder.style.side = {
                ft.ControlState.DEFAULT: ft.BorderSide(0),
                ft.ControlState.HOVERED: ft.BorderSide(3, ft.Colors.BLUE_ACCENT_400),
            }

        # Apply selected border
        btn.style.side = {
            ft.ControlState.DEFAULT: ft.BorderSide(3, ft.Colors.BLUE_ACCENT_400),
        }

        self.selected_folder = btn
        self.show_folder(node)
        self.page.update()

    def show_folder(self, folder):
        self.bookmarks.controls.clear()

        dl = folder.next
        try:
            while dl and dl.tag != 'dl':
                dl = dl.next

            if not dl:
                print("DL not found for folder")
                return

            child = dl.child

            while child:
                if child.tag == 'dt':
                    inner = child.child
                    while inner:
                        if inner.tag == 'a':
                            bookmark = Bookmark(
                                page_name=inner.text(),
                                link=inner.attributes.get('href'),
                                on_bookmark_delete=self.bookmark_delete
                            )
                            bookmark.node = child
                            bookmark.callback_show_preview = self.show_preview
                            self.bookmarks.controls.append(bookmark)
                        inner = inner.next
                child = child.next
            self.update()
        except Exception as e:
            print(e)

    def start_button_clicked(self):
        # Clear app controls, hide complete message, show progress bar
        self.start_button.bgcolor = "grey"
        self.saved.visible = False
        self.complete.visible = False
        self.progressbar.visible = True
        self.progressbar.value = 0
        self.bookmarks.controls.clear()
        self.folders_column.controls.clear()
        self.page.update()

        html = self.input_field.value
        self.tree = LexborHTMLParser(html)
        self.result = ''

        root_dl = self.tree.css_first('dl')

        if root_dl:
            self.progressbar.value = 0.4
            self.update()
            self.parse_dl(root_dl)

        bookmarks_file = os.path.join(application_dir, "!edited_bookmarks.txt")
        with open(bookmarks_file, 'w', encoding="utf-8") as file:
            file.write(self.result)
            self.progressbar.value = 1.0
            self.update()

        # Hide progressbar, show complete message, clear input field
        self.progressbar.visible = False
        self.progressbar.value = 0
        self.complete.visible = True
        self.input_field.value = ''
        self.page.update()

    def save_button_clicked(self):
        try:
            self.start_button.bgcolor = "white"
            self.complete.visible = False
            self.saved.visible = True
            self.update()
            edited_bookmarks_file = os.path.join(application_dir, "!edited_bookmarks.html")
            with open(edited_bookmarks_file, 'w', encoding="utf-8") as file:
                file.write(self.tree.html)
        except AttributeError:
            pass

    def bookmark_delete(self, bookmark):
        # Remove from html tree
        if bookmark.node:
            bookmark.node.decompose()
            bookmark.node = None

        # Remove from UI
        self.bookmarks.controls.remove(bookmark)
        self.update()


def main(page: ft.Page):
    page.title = "Bookmark Curator"
    page.window.width = 900
    page.window.height = 800
    page.bgcolor = '#E1E4E8'
    page.padding = 20
    page.update()

    app = BookmarkApp()


    # -------------------------------
    # Credits
    # -------------------------------

    heart_icon = ft.Icon(ft.Icons.FAVORITE, color="black", size=20)
    credit_message = ft.Text(value="made by ShuraShved", color="black")
    credentials_row = ft.Row(
        controls=[heart_icon, credit_message],
        alignment=ft.MainAxisAlignment.END,
    )


    # -------------------------------
    # Main section
    # -------------------------------

    right_scroll = ft.ListView(
        expand=True,
        spacing=5,
        controls=[app],
    )

    main_panel = ft.Container(
        expand=True,
        bgcolor='#BCC6CC',
        padding=ft.Padding.symmetric(horizontal=40, vertical=20),
        content=right_scroll,
    )

    left_scroll = ft.ListView(
        expand=True,
        spacing=5,
        controls=[app.folders_column],
    )

    folders_panel = ft.Container(
        width=260,
        bgcolor=ft.Colors.BLUE_GREY_200,
        padding=10,
        content=left_scroll,
    )

    row_app = ft.Row(
        expand=True,
        controls=[
            folders_panel,
            main_panel
        ]
    )


    # -------------------------------
    # On Close App
    # -------------------------------

    page.on_close = lambda e: page.run_task(app.preview_gen.close_browser)


    # -------------------------------
    # Page
    # -------------------------------

    page.add(
        row_app,
        credentials_row,
    )
    page.update()

if __name__ == "__main__":
    ft.run(main)
ft.app(target=main, assets_dir="assets")