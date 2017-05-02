#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of nautilus-telegram-uploader
#
# Copyright (C) 2016 Lorenzo Carbonell
# lorenzo.carbonell.cerezo@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
#
import gi
try:
    gi.require_version('Gtk', '3.0')
    gi.require_version('GdkPixbuf', '2.0')
    gi.require_version('Nautilus', '3.0')
except Exception as e:
    print(e)
    exit(-1)
import os
import json

from urllib import unquote_plus
import time
import pexpect
import unicodedata
import sys
import subprocess
import shlex
import re

from threading import Thread
from gi.repository import GObject

from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Nautilus as FileManager

APP = '$APP$'
VERSION = '$VERSION$'

CONFIG_APP_DIR = os.path.join(os.path.expanduser('~'), '.telegram-cli')
CONFIG_FILE = os.path.join(CONFIG_APP_DIR, '{0}.conf'.format(APP))
if not os.path.exists(CONFIG_APP_DIR):
    os.makedirs(CONFIG_APP_DIR)

IMAGE_EXTENSIONS = ['.bmp', '.dds', '.exif', '.gif', '.jpg', '.jpeg', '.jp2',
                    '.jpx', '.pcx', '.png', '.pnm', '.ras', '.tga', '.tif',
                    '.tiff', '.xbm', '.xpm']
VIDEO_EXTENSIONS = ['.mp4']
AUDIO_EXTENSIONS = ['.mp3']


_ = str


def select_value_in_combo(combo, value):
    model = combo.get_model()
    for i, item in enumerate(model):
        if value == item[0]:
            combo.set_active(i)
            return
    combo.set_active(0)


def get_selected_value_in_combo(combo):
    model = combo.get_model()
    return model.get_value(combo.get_active_iter(), 0)


def sleep(sleep_time=250):
    t = int(round(time.time() * 1000))
    while int(round(time.time() * 1000)) - t < sleep_time:
        Gtk.main_iteration()


def send(media, peer, afile):
    peer = peer.replace(' ', '_')
    cmd = 'telegram-cli -C -W -e \'send_{0} {1} "{2}"\''.format(media, peer,
                                                                afile)
    args = shlex.split(cmd)
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    data1, data2 = p.communicate()
    ansi_escape = re.compile(r'\x1b[^m]*m')
    data1 = ansi_escape.sub('', data1.decode('utf-8'))
    data1 = unicodedata.normalize('NFKD', data1).encode('ascii', 'ignore')
    data2 = ansi_escape.sub('', data2.decode('utf-8'))
    data2 = unicodedata.normalize('NFKD', data2).encode('ascii', 'ignore')
    if data1.find('All done') > -1 and len(data2) == 0:
        return True
    return False


def send_photo(peer, afile):
    return send('photo', peer, afile)


def send_video(peer, afile):
    return send('video', peer, afile)


def send_audio(peer, afile):
    return send('audio', peer, afile)


def send_file(peer, afile):
    return send('file', peer, afile)


def get_contacts_from_telegram_cli():
    cmd = 'telegram-cli -C -W -e "contact_list"'
    args = shlex.split(cmd)
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    data1, data2 = p.communicate()
    ansi_escape = re.compile(r'\x1b[^m]*m')
    ans = ansi_escape.sub('', data1.decode('utf-8'))
    ans = unicodedata.normalize('NFKD', ans).encode('ascii', 'ignore')
    print('----')
    print(ans)
    print('----')
    ans = ans.encode('utf-8').replace('\r', '\n').split('\n')[8:-3]
    contacts = []
    for element in ans:
        if element.startswith('> ') or element.startswith(' [') or\
                element.startswith('  '):
            pass
        else:
            contacts.append(element)
    contacts = sorted(contacts, key=lambda s: s.lower())
    return contacts


def get_contacts():
    config = {}
    contacts = []
    if os.path.exists(os.path.join(CONFIG_APP_DIR, 'auth')):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
    if config:
        contacts = config['contacts']
    else:
        contacts = get_contacts_from_telegram_cli()
        config['contacts'] = contacts
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    return contacts


class IdleObject(GObject.GObject):
    """
    Override GObject.GObject to always emit signals in the main thread
    by emmitting on an idle handler
    """
    def __init__(self):
        GObject.GObject.__init__(self)

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)


class PhoneDialog(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, _('Telegram-cli'), parent,
                            Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,
                             Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_title(APP)
        #
        vbox = Gtk.VBox(spacing=5)
        self.get_content_area().add(vbox)
        hbox1 = Gtk.HBox()
        vbox.pack_start(hbox1, True, True, 10)
        #
        label = Gtk.Label(_('Phone') + ' :')
        hbox1.pack_start(label, True, True, 10)

        self.entry = Gtk.Entry()
        hbox1.pack_start(self.entry, True, True, 0)
        #
        self.show_all()


class CodeDialog(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, _('Telegram-cli'), parent,
                            Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,
                             Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_title(APP)
        #
        vbox = Gtk.VBox(spacing=5)
        self.get_content_area().add(vbox)
        hbox1 = Gtk.HBox()
        vbox.pack_start(hbox1, True, True, 10)
        #
        label = Gtk.Label(_('Code') + ' :')
        hbox1.pack_start(label, True, True, 10)

        self.entry = Gtk.Entry()
        hbox1.pack_start(self.entry, True, True, 0)
        #
        self.show_all()


class SendDialog(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, _('Telegram-cli'), parent,
                            Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,
                             Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_title(APP)
        #
        vbox = Gtk.VBox(spacing=5)
        self.get_content_area().add(vbox)
        hbox1 = Gtk.HBox()
        vbox.pack_start(hbox1, True, True, 10)
        #
        label = Gtk.Label(_('Select contact') + ' :')
        hbox1.pack_start(label, True, True, 10)

        contactsstore = Gtk.ListStore(str)
        for contact in get_contacts():
            contactsstore.append([contact])
        self.comboboxcontacts = Gtk.ComboBox.new()
        self.comboboxcontacts.set_model(contactsstore)
        cell1 = Gtk.CellRendererText()
        self.comboboxcontacts.pack_start(cell1, True)
        self.comboboxcontacts.add_attribute(cell1, 'text', 0)
        self.comboboxcontacts.set_active(0)
        hbox1.pack_start(self.comboboxcontacts, True, True, 10)
        #
        self.show_all()

    def get_selected(self):
        return get_selected_value_in_combo(self.comboboxcontacts)


class RegisterTelegramCli(IdleObject, Thread):
    __gsignals__ = {
        'code': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
        'ended': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, phone):
        IdleObject.__init__(self)
        Thread.__init__(self)
        self.phone = phone
        self.code = None
        self.gotit = False
        self.stopit = False
        self.ok = False
        self.daemon = True

    def set_code(self, code):
        self.code = code
        self.gotit = True

    def run(self):
        try:
            child = pexpect.spawn('telegram-cli -e contact_list')
            child.logfile = sys.stdout
            child.expect_exact('phone number:')
            child.sendline(self.phone)
            child.expect_exact("code ('CALL' for phone code):")
            # child.expect('code ')
            self.emit('code')
            print('code')
            while self.gotit is False:
                sleep(200)
            child.sendline(self.code)
            child.expect('updated flags')
            child.close()
        except Exception as e:
            print(e)
            self.ok = False


class DoItInBackground(IdleObject, Thread):
    __gsignals__ = {
        'started': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'ended': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (bool,)),
        'start_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'end_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (float,)),
    }

    def __init__(self, peer, files):
        IdleObject.__init__(self)
        Thread.__init__(self)
        self.peer = peer
        self.elements = files
        self.stopit = False
        self.ok = False
        self.daemon = True

    def stop(self, *args):
        self.stopit = True

    def send_file(self, file_in):
        filename, file_extension = os.path.splitext(file_in)
        if file_extension.lower() in IMAGE_EXTENSIONS:
            self.tb.send_photo(self.peer, file_in)
        elif file_extension.lower() in VIDEO_EXTENSIONS:
            self.tb.send_video(self.peer, file_in)
        elif file_extension.lower() in AUDIO_EXTENSIONS:
            self.tb.send_audio(self.peer, file_in)
        else:
            self.tb.send_document(self.peer, file_in)

    def run(self):
        total = 0
        for element in self.elements:
            total += get_duration(element)
        self.emit('started', total)
        try:
            self.ok = True
            for element in self.elements:
                if self.stopit is True:
                    self.ok = False
                    break
                self.emit('start_one', element)
                self.send_file(element)
                self.emit('end_one', get_duration(element))
        except Exception as e:
            print(e)
            self.ok = False
        self.emit('ended', self.ok)


class Progreso(Gtk.Dialog, IdleObject):
    __gsignals__ = {
        'i-want-stop': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, title, parent, max_value):
        Gtk.Dialog.__init__(self, title, parent,
                            Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT)
        IdleObject.__init__(self)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(330, 30)
        self.set_resizable(False)
        self.connect('destroy', self.close)
        self.set_modal(True)
        vbox = Gtk.VBox(spacing=5)
        vbox.set_border_width(5)
        self.get_content_area().add(vbox)
        #
        frame1 = Gtk.Frame()
        vbox.pack_start(frame1, True, True, 0)
        table = Gtk.Table(2, 2, False)
        frame1.add(table)
        #
        self.label = Gtk.Label()
        table.attach(self.label, 0, 2, 0, 1,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK,
                     yoptions=Gtk.AttachOptions.EXPAND)
        #
        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_size_request(300, 0)
        table.attach(self.progressbar, 0, 1, 1, 2,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK,
                     yoptions=Gtk.AttachOptions.EXPAND)
        button_stop = Gtk.Button()
        button_stop.set_size_request(40, 40)
        button_stop.set_image(
            Gtk.Image.new_from_stock(Gtk.STOCK_STOP, Gtk.IconSize.BUTTON))
        button_stop.connect('clicked', self.on_button_stop_clicked)
        table.attach(button_stop, 1, 2, 1, 2,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK)
        self.stop = False
        self.show_all()
        self.max_value = float(max_value)
        self.value = 0.0

    def set_max_value(self, anobject, max_value):
        self.max_value = float(max_value)

    def get_stop(self):
        return self.stop

    def on_button_stop_clicked(self, widget):
        self.stop = True
        self.emit('i-want-stop')

    def close(self, *args):
        self.destroy()

    def increase(self, anobject, value):
        self.value += float(value)
        fraction = self.value / self.max_value
        self.progressbar.set_fraction(fraction)
        if self.value >= self.max_value:
            self.hide()

    def set_element(self, anobject, element):
        self.label.set_text(_('Sending: %s') % element)


def get_duration(file_in):
    return os.path.getsize(file_in)


def get_files(files_in):
    files = []
    for file_in in files_in:
        file_in = unquote_plus(file_in.get_uri()[7:])
        if os.path.isfile(file_in):
            files.append(file_in)
    return files


class TelegramCliUploaderMenuProvider(GObject.GObject,
                                      FileManager.MenuProvider):

    def __init__(self):
        self.contacts = get_contacts()

    def all_files_are_files(self, items):
        for item in items:
            if not os.path.isfile(unquote_plus(item.get_uri()[7:])):
                return False
        return True

    def send_files(self, menu, selected, window):
        files = get_files(selected)
        if len(files) > 0:
            sd = SendDialog(window)
            if sd.run() == Gtk.ResponseType.ACCEPT:
                contact = sd.get_selected().replace(' ', '_')
                diib = DoItInBackground(contact,
                                        files)
                progreso = Progreso(_('Send files to telegram'),
                                    window,
                                    len(files))
                diib.connect('started', progreso.set_max_value)
                diib.connect('start_one', progreso.set_element)
                diib.connect('end_one', progreso.increase)
                diib.connect('ended', progreso.close)
                progreso.connect('i-want-stop', diib.stop)
                diib.start()
                progreso.run()

    def get_file_items(self, window, sel_items):
        top_menuitem = FileManager.MenuItem(
            name='TelegramCliUploaderMenuProvider::Gtk-telegram-top',
            label=_('telegram...'),
            tip=_('Send files to telegram'))
        submenu = FileManager.Menu()
        top_menuitem.set_submenu(submenu)
        sub_menuitem_00 = FileManager.MenuItem(
            name='TelegramCliUploaderMenuProvider::Gtk-telegram-sub-00',
            label=_('Send...'),
            tip='Send files to telegram')
        sub_menuitem_00.connect('activate', self.send_files, sel_items,
                                window)
        submenu.append_item(sub_menuitem_00)

        if self.all_files_are_files(sel_items) and \
                os.path.exists(os.path.join(CONFIG_APP_DIR, 'auth')):
            sub_menuitem_00.set_property('sensitive', True)
        else:
            sub_menuitem_00.set_property('sensitive', False)

        sub_menuitem_02 = FileManager.MenuItem(
            name='TelegramCliUploaderMenuProvider::Gtk-telegram-sub-02',
            label=_('About'),
            tip=_('About'))
        sub_menuitem_02.connect('activate', self.about, window)
        submenu.append_item(sub_menuitem_02)

        return top_menuitem,

    def about(self, widget, window):
        ad = Gtk.AboutDialog(parent=window)
        ad.set_name(APP)
        ad.set_version(VERSION)
        ad.set_copyright('Copyrignt (c) 2017\nLorenzo Carbonell')
        ad.set_comments(APP)
        ad.set_license('''
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
''')
        ad.set_website('http://www.atareao.es')
        ad.set_website_label('http://www.atareao.es')
        ad.set_authors([
            'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
        ad.set_documenters([
            'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
        ad.set_icon_name(APP)
        ad.set_logo_icon_name(APP)
        ad.run()
        ad.destroy()


if __name__ == '__main__':
    # print(send_file('atareao', '/home/lorenzo/PDF/pendientes.pdf'))
    sd = SendDialog(None)
    if sd.run() == Gtk.ResponseType.ACCEPT:
        print(sd.get_selected())
        print(send_file('{0}'.format(sd.get_selected()),
              '/home/lorenzo/PDF/pendientes.pdf'))
