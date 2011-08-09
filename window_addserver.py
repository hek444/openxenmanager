# -----------------------------------------------------------------------
# OpenXenManager
#
# Copyright (C) 2009 Alberto Gonzalez Rodriguez alberto@pesadilla.org
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------
#!/usr/bin/env python
import xtea
from oxcSERVER import *
class oxcWindowAddServer:
    """
    Class with functions to manage "add server" window
    """
    def on_addserver_clicked(self, widget, data=None):
        """
        Function called when you press "add server" button 
        """
        # Show the add server window
        self.builder.get_object("addserver").show_all()
        self.builder.get_object("addserverhostname").grab_focus()
    def on_imageaddserver_button_press_event(self, widget, data=None):
        """
        Function called when you press main image to add "add server"
        """
        # Show the add server window
        self.builder.get_object("addserver").show()
        self.builder.get_object("addserverpassword").grab_focus()
    def on_addserverhostname_changed(self, widget, data=None):
        """
        Function called when hostname/ip text field is changed
        """
        # Get "connect" button object
        connectAddServer = self.builder.get_object("connectAddServer")
        # widget.get_active_text() contains the ip/hostname
        if len(widget.get_active_text()) > 0:
            # If is not empty, enable the button
            connectAddServer.set_sensitive(True)
        else:
            # If is empty, disable the button
            connectAddServer.set_sensitive(False)
    def on_connectAddServer_clicked(self, widget, data=None):
        """
        Function called when you press the "connect" button 
        """
        # Get host, username and password
        host = self.builder.get_object("addserverhostname").get_active_text()
        user = self.builder.get_object("addserverusername").get_text()
        password = self.builder.get_object("addserverpassword").get_text()
        # Call to "add_server" function with params
        # This function try connect to server and authenticate
        self.add_server(host, user, password)
    def on_cancelAddServer_clicked(self, widget, data=None):
        """
        Function called when you press the "cancel" button on "add server" dialog
        """
        self.builder.get_object("addserver").hide()
    def update_progressconnect(self):
        """
        Function to update "progress connect" while is loading
        """
        #gtk.gdk.threads_enter()
        self.builder.get_object("progressconnect").pulse()
        #gtk.gdk.threads_leave()
        
    def add_server(self, host, user, password, iter=None, ssl = None):
        """
        Function used to connect to server
        """
        self.builder.get_object("addserver").hide()
        #Show a dialog with a progress bar.. it should be do better
        self.builder.get_object("wprogressconnect").show()
        # Check if SSL connection is selected
        if ssl == None:
            ssl = self.builder.get_object("checksslconnection").get_active()
        else:
            self.builder.get_object("checksslconnection").set_active(ssl)
        
        # Create a new oxcSERVER object
        self.builder.get_object("lblprogessconnect").set_label("Connecting to %s..." % host)
        server = oxcSERVER(host,user,password, self, ssl)
        self.xc_servers[host] = server
        # connect the signal handlers
        server.connect("connect-success", self.server_connect_success)
        server.connect("connect-failure", self.server_connect_failure)
        server.connect("sync-progress", self.server_sync_progress)
        server.connect("sync-success", self.server_sync_update_tree)
        server.connect("sync-failure", self.server_sync_failure)
        # begin async connection
        server.connect_server_async()
        # begin UI animation
        Thread(target=self.update_connect_status, args=(server,)).start()
    
    def update_connect_status(self, server):
        """Animates the progress bar during connection.
        """
        while server.connectThread.isAlive():
            self.builder.get_object("progressconnect").pulse()
            server.connectThread.join(1)
        # TODO: what does this variable do?
        if self.selected_host == None:
            self.selected_host = server.host
        
    def server_connect_success(self, server):
        """Callback when a server connects successfully.
        
        We begin "synchronising", where the server object downloads data
        about the server, and then we query it to update our UI
        """
        # Hide "add server" window
        self.builder.get_object("addserver").hide()
        # Append to historical host list on "add server" window
        self.builder.get_object("listaddserverhosts").append([server.host])
        # Remove the server from tree; it will be created again with "server_sync_update_tree"
        (model, iter) = self.treeview.get_selection().get_selected()
        iter = self.modelfilter.convert_iter_to_child_iter(iter)
        assert self.treestore.iter_is_valid(iter)
        if self.treestore.get_value(iter, 3) == "server":
            self.treestore.remove(iter)
        # Fill left tree and get all data (pool, vm, storage, template..)
        Thread(target=server.sync).start()
        
        # If we use a master password then save the password
        # Password is saved encrypted with XTEA
        encrypted_password = ""
        if self.password:
            x = xtea.crypt("X" * (16-len(self.password)) + self.password, server.password, self.iv)
            encrypted_password = x.encode("hex")
        self.config_hosts[server.host] = [server.user, encrypted_password, server.ssl]
        self.config['servers']['hosts'] = self.config_hosts
        # Save relation host/user/passwords to configuration
        self.config.write()
    
    def server_connect_failure(self, server, msg):
        """Method called if connection fails
        """
        # Show add server dialog again
        self.builder.get_object("addserver").show()
        # And hide progress bar
        self.builder.get_object("wprogressconnect").hide()
        # Show an alert dialog showing error
        self.show_error_dlg("%s" % msg, "Error connecting")
        
    def server_sync_progress(self, server, msg):
        self.builder.get_object("progressconnect").pulse()
        self.builder.get_object("lblprogessconnect").set_text("Synchronizing...\n%s" % msg)
        
    
    def server_sync_finish(self, server):
        # Hide window progress
        self.builder.get_object("wprogressconnect").hide()
        
        # Setting again the modelfiter it will be refresh internal path/references
        self.treeview.set_model(self.modelfilter)
        self.treeview.expand_all()

    def server_sync_failure(self, server, msg):
        self.show_error_dlg(msg)
        self.server_sync_finish(server)

    def server_sync_update_tree(self, server):
        """Method called when connection loading is finished
        """
        gtk.gdk.threads_enter()
        
        # TODO: csun: clean this up
        
        poolroot = None 
        hostroot = {}
        root = ""
        server.treestore = self.treestore
        server.default_sr = ""
        
        for pool in server.all_pools.keys():
            server.default_sr = server.all_pools[pool]['default_SR']
            if server.all_pools[pool]['name_label']:
                poolroot =  self.treestore.append(self.treeroot, [gtk.gdk.pixbuf_new_from_file\
                    ("images/poolconnected_16.png"),\
                    server.all_pools[pool]['name_label'], pool, "pool", "Running", server.host, pool, ['newvm', 'newstorage', 'importvm', 'disconnect'], server.host])
        if poolroot:
            relacion = {}
            for ref in server.all_hosts.keys():
                relacion[str(server.all_hosts[ref]['name_label'] + "_" + ref)] = ref
            server.all_hosts_keys = []
            rkeys = relacion.keys()
            rkeys.sort(key=str.lower)
            for ref in rkeys:
                server.all_hosts_keys.append(relacion[ref])
            for h in server.all_hosts_keys:
                host_uuid = server.all_hosts[h]['uuid']
                host = server.all_hosts[h]['name_label']
                host_enabled = server.all_hosts[h]['enabled']
                host_address = server.all_hosts[h]['address']
                if host_enabled:
                    hostroot[h] = self.treestore.append(poolroot, [gtk.gdk.pixbuf_new_from_file\
                                ("images/tree_connected_16.png"),\
                                host, host_uuid, "host", "Running", server.host, h,\
                                ['newvm', 'importvm', 'newstorage', 'clean_reboot', 'clean_shutdown', 'shutdown'], host_address])
                else:
                    hostroot[h] = self.treestore.append(poolroot, [gtk.gdk.pixbuf_new_from_file\
                                ("images/tree_disabled_16.png"),\
                                host, host_uuid, "host", "Disconnected", server.host, h, \
                                [], host_address])
            root = poolroot
        else:
           host_uuid = server.all_hosts[server.all_hosts.keys()[0]]['uuid']
           host = server.all_hosts[server.all_hosts.keys()[0]]['name_label']
           host_address = server.all_hosts[server.all_hosts.keys()[0]]['address']
           host_enabled = server.all_hosts[server.all_hosts.keys()[0]]['enabled']
           if host_enabled:
               hostroot[server.all_hosts.keys()[0]] = self.treestore.append(self.treeroot, [gtk.gdk.pixbuf_new_from_file\
                            ("images/tree_connected_16.png"),\
                            host, host_uuid, "host", "Running", server.host, server.all_hosts.keys()[0], 
                            ['newvm', 'importvm', 'newstorage', 'clean_reboot', 'clean_shutdown', 'shutdown', 'disconnect'], host_address])
           else:
               hostroot[server.all_hosts.keys()[0]] = self.treestore.append(self.treeroot, [gtk.gdk.pixbuf_new_from_file\
                            ("images/tree_disabled_16.png"),\
                            host, host_uuid, "host", "Running", server.host, server.all_hosts.keys()[0], 
                            ['newvm', 'importvm', 'newstorage', 'clean_reboot', 'clean_shutdown', 'shutdown', 'disconnect'], host_address])
           root = hostroot[server.all_hosts.keys()[0]]
        server.hostname = host
        server.hostroot = hostroot
        server.poolroot = poolroot
        relacion = {}
        for ref in server.all_vms.keys():
            relacion[str(server.all_vms[ref]['name_label'] + "_" + ref)] = ref
        server.all_vms_keys = []
        rkeys = relacion.keys()
        rkeys.sort(key=str.lower)
        for ref in rkeys:
            server.all_vms_keys.insert(0,relacion[ref])


        for vm in server.all_vms_keys:
            if not server.all_vms[vm]['is_a_template']:
                if not server.all_vms[vm]['is_control_domain']:
                  server.add_vm_to_tree(vm)
                  for operation in server.all_vms[vm]["current_operations"]:
                    server.track_tasks[operation] = vm
                else:
                  server.host_vm[server.all_vms[vm]['resident_on']] = [vm,  server.all_vms[vm]['uuid']]
  
        # Get all storage record 
        for sr in server.all_storage.keys():
            if server.all_storage[sr]['name_label'] != "XenServer Tools":
                if len(server.all_storage[sr]['PBDs']) == 0:
                    server.last_storage_iter = self.treestore.append(root, [\
                           gtk.gdk.pixbuf_new_from_file("images/storage_detached_16.png"),\
                             server.all_storage[sr]['name_label'], server.all_storage[sr]['uuid'],\
                             "storage", None, server.host, sr, server.all_storage[sr]['allowed_operations'], None])
                    continue
                broken = False
                for pbd_ref in server.all_storage[sr]['PBDs']:
                    if not server.all_pbd[pbd_ref]['currently_attached']:
                        broken = True
                        server.last_storage_iter = self.treestore.append(root, [\
                               gtk.gdk.pixbuf_new_from_file("images/storage_broken_16.png"),\
                                 server.all_storage[sr]['name_label'], server.all_storage[sr]['uuid'],\
                                 "storage", None, server.host, sr, server.all_storage[sr]['allowed_operations'], None])
                if not broken:
                    if server.all_storage[sr]['shared']:
                        if sr == server.default_sr:
                            server.last_storage_iter = self.treestore.append(root, [\
                               gtk.gdk.pixbuf_new_from_file("images/storage_default_16.png"),\
                                 server.all_storage[sr]['name_label'], server.all_storage[sr]['uuid'],\
                                 "storage", None, server.host, sr, server.all_storage[sr]['allowed_operations'], None])
                        else:
                            server.last_storage_iter = self.treestore.append(root, [\
                               gtk.gdk.pixbuf_new_from_file("images/storage_shaped_16.png"),\
                                 server.all_storage[sr]['name_label'], server.all_storage[sr]['uuid'],\
                                 "storage", None, server.host, sr, server.all_storage[sr]['allowed_operations'], None])

                    else:
                        for pbd in server.all_storage[sr]['PBDs']:
                            if sr == server.default_sr:
                                if server.all_pbd[pbd]['host'] in hostroot:
                                    server.last_storage_iter = self.treestore.append(hostroot[server.all_pbd[pbd]['host']], [\
                                        gtk.gdk.pixbuf_new_from_file("images/storage_default_16.png"),\
                                         server.all_storage[sr]['name_label'], server.all_storage[sr]['uuid'],\
                                         "storage", None, server.host, sr, server.all_storage[sr]['allowed_operations'], None])
                                else:
                                    server.last_storage_iter = self.treestore.append(root, [\
                                       gtk.gdk.pixbuf_new_from_file("images/storage_shaped_16.png"),\
                                         server.all_storage[sr]['name_label'], server.all_storage[sr]['uuid'],\
                                         "storage", None, server.host, sr, server.all_storage[sr]['allowed_operations'], None])

                            else:
                                if server.all_pbd[pbd]['host'] in hostroot:
                                    server.last_storage_iter = self.treestore.append(hostroot[server.all_pbd[pbd]['host']], [\
                                        gtk.gdk.pixbuf_new_from_file("images/storage_shaped_16.png"),\
                                         server.all_storage[sr]['name_label'], server.all_storage[sr]['uuid'],\
                                         "storage", None, server.host, sr, server.all_storage[sr]['allowed_operations'], None])
                                else:
                                    server.last_storage_iter = self.treestore.append(root, [\
                                       gtk.gdk.pixbuf_new_from_file("images/storage_shaped_16.png"),\
                                         server.all_storage[sr]['name_label'], server.all_storage[sr]['uuid'],\
                                         "storage", None, server.host, sr, server.all_storage[sr]['allowed_operations'], None])


                    
        for tpl in server.all_vms_keys:
            if server.all_vms[tpl]['is_a_template'] and not server.all_vms[tpl]['is_a_snapshot']: 
                if server.all_vms[tpl]['last_booted_record'] == "":
                     self.treestore.append(root, [\
                        gtk.gdk.pixbuf_new_from_file("images/template_16.png"),\
                        server.all_vms[tpl]['name_label'], server.all_vms[tpl]['uuid'],\
                        "template", None, server.host, tpl, server.all_vms[tpl]['allowed_operations'], None])
                else:
                     tpl_affinity = server.all_vms[tpl]['affinity']
                    
                     if tpl_affinity in hostroot: 
                         self.treestore.append(hostroot[tpl_affinity], [\
                            gtk.gdk.pixbuf_new_from_file("images/user_template_16.png"),\
                            server.all_vms[tpl]['name_label'], server.all_vms[tpl]['uuid'],\
                            "custom_template", None, server.host, tpl, server.all_vms[tpl]['allowed_operations'], None])
                     else:
                         self.treestore.append(root, [\
                            gtk.gdk.pixbuf_new_from_file("images/user_template_16.png"),\
                            server.all_vms[tpl]['name_label'], server.all_vms[tpl]['uuid'],\
                            "custom_template", None, server.host, tpl, server.all_vms[tpl]['allowed_operations'], None])

        self.treeview.expand_all()
        
        gtk.gdk.threads_leave()
        
        # Create a new thread it receives updates
        self.xc_servers[self.selected_host].thread_event_next()
        # Fill alerts list on "alerts" window
        self.xc_servers[self.selected_host].fill_alerts(self.listalerts)
        self.update_n_alerts()
        
        self.server_sync_finish(server)