# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

      config.vm.box = "chef/ubuntu-14.04"

    config.vm.define "db" do |db|
        db.vm.network "private_network", ip: "10.64.7.101"
        db.vm.provider "virtualbox" do |vb|
            vb.name = "db.thezombies"
            vb.memory = 768
        end

        db.vm.provision "ansible" do |ansible|
            ansible.playbook = "provisioning/db.yaml"
            ansible.inventory_path = "provisioning/hosts.vagrant"
            ansible.limit = "all"
            ansible.extra_vars = { deploy_type: "vagrant" }
            ansible.raw_arguments = ["-T 30"]
        end
    end

    config.vm.define "broker" do |broker|
        broker.vm.network "private_network", ip: "10.64.7.103"
        broker.vm.synced_folder "./", "/projects/thezombies/src/thezombies"

        broker.vm.provider "virtualbox" do |vb|
            vb.name = "broker.thezombies"
            vb.memory = 1024
        end

        broker.vm.provision "ansible" do |ansible|
            ansible.playbook = "provisioning/broker.yaml"
            ansible.inventory_path = "provisioning/hosts.vagrant"
            ansible.limit = "all"
            ansible.extra_vars = { deploy_type: "vagrant" }
            ansible.raw_arguments = ["-T 30"]
        end
    end

    config.vm.define "workers" do |workers|
        workers.vm.network "private_network", ip: "10.64.7.102"
        workers.vm.synced_folder "./", "/projects/thezombies/src/thezombies"

        workers.vm.provider "virtualbox" do |vb|
            vb.name = "workers.thezombies"
            vb.memory = 2048
            vb.cpus = 4
        end

        workers.vm.provision "ansible" do |ansible|
            ansible.playbook = "provisioning/workers.yaml"
            ansible.inventory_path = "provisioning/hosts.vagrant"
            ansible.limit = "all"
            ansible.extra_vars = { deploy_type: "vagrant" }
            ansible.raw_arguments = ["-T 30"]
        end
    end

    config.vm.define "site" do |site|
        site.vm.network "private_network", ip: "10.64.7.100"
        site.vm.synced_folder "./", "/projects/thezombies/src/thezombies"

        site.vm.provider "virtualbox" do |vb|
            vb.name = "www.thezombies"
        end

        site.vm.provision "ansible" do |ansible|
            ansible.playbook = "provisioning/site.yaml"
            ansible.inventory_path = "provisioning/hosts.vagrant"
            ansible.limit = "all"
            ansible.extra_vars = { deploy_type: "vagrant" }
            ansible.raw_arguments = ["-T 30"]
        end
    end
end
