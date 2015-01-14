# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

      config.vm.box = "chef/ubuntu-14.04"

    config.vm.define "site" do |site|
        site.vm.network "private_network", ip: "10.64.7.100"
        config.vm.provider "virtualbox" do |vb|
            vb.name = "www.thezombies"
            vb.memory = 2048
        end

        config.vm.provision "ansible" do |ansible|
            ansible.playbook = "provisioning/site.yaml"
            ansible.inventory_path = "ansible/hosts.vagrant"
            ansible.extra_vars = { deploy_type: "vagrant" }
        end
    end

    config.vm.define "db" do |site|
        site.vm.network "private_network", ip: "10.64.7.101"
        config.vm.provider "virtualbox" do |vb|
            vb.name = "db.thezombies"
            vb.memory = 1024
        end

        config.vm.provision "ansible" do |ansible|
            ansible.playbook = "provisioning/db.yaml"
            ansible.inventory_path = "ansible/hosts.vagrant"
            ansible.extra_vars = { deploy_type: "vagrant" }
        end
    end

end
