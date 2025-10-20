
/* This file is part of Jeedom.
 *
 * Jeedom is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Jeedom is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Jeedom. If not, see <http://www.gnu.org/licenses/>.
 */

 $("#table_cmd").sortable({axis: "y", cursor: "move", items: ".cmd", placeholder: "ui-state-highlight", tolerance: "intersect", forcePlaceholderSize: true});
/*
 * Fonction pour l'ajout de commande, appellé automatiquement par plugin.template
 */
 function addCmdToTable(_cmd) {
    if (!isset(_cmd)) {
        var _cmd = {configuration: {}};
    }
    if (!isset(_cmd.configuration)) {
        _cmd.configuration = {};
    }
    var tr = '<tr class="cmd" data-cmd_id="' + init(_cmd.id) + '">';
    
    tr += '<td>';
    tr += '<span class="cmdAttr" data-l1key="id" style="display:none;"></span>';
    tr += '<div class="row">';
    tr += '<div class="col-sm-5">';    
    tr += '<a class="cmdAction btn btn-default btn-sm" data-l1key="chooseIcon"><i class="fas fa-flag"></i> Icone</a>';
    tr += '<span class="cmdAttr" data-l1key="display" data-l2key="icon" style="margin-left : 10px;"></span>';
    tr += '</div>';
    tr += '<div class="col-sm-7">';
    tr += '<input class="cmdAttr form-control input-sm" data-l1key="name" placeholder="{{Nom}}">';  
    tr += '</div>';
    tr += '</div>';  
    if (init(_cmd.logicalId) !='refresh') {
      tr += '<select class="cmdAttr form-control input-sm" data-l1key="value" style="display : none;margin-top : 5px;" title="La valeur de la commande vaut par défaut la commande">';
      tr += '<option value="">Aucune</option>';
      tr += '</select>';
    }
    tr += '</td>';

    tr += '<td>';
    tr += '<span class="type" type="' + init(_cmd.type) + '" style="">' + jeedom.cmd.availableType() + '</span>';
    tr += '<span class="subType" subType="' + init(_cmd.subType) + '" style=""></span>';
    tr += '</td>';
    
    tr += '<td>';
    tr += '<input class="cmdAttr form-control input-sm" data-l1key="logicalId">';
    tr += '</td>';

    tr += '<td>';
    //tr += '<input class="cmdAttr form-control input-sm" data-l1key="configuration" data-l2key="eqType" placeholder="{{Catégorie}}" >';
   	tr += '<select class="cmdAttr form-control input-sm" data-l1key="configuration" data-l2key="eqType">';
		tr += '<option value="input">{{Source}}</option>';
    tr += '<option value="sound">{{Audio}}</option>';
    tr += '<option value="volume">{{Volume Sonore}}</option>';
    tr += '<option value="power">{{Alimentation}}</option>';
    tr += '<option value="tuner">{{Radio}}</option>';
    tr += '<option value="other">{{Autre}}</option>';
    tr += '</select>';
    tr += '</td>';

    tr += '<td>'
    tr += '<label class="checkbox-inline"><input type="checkbox" class="cmdAttr" data-l1key="isVisible" checked/>{{Afficher}}</label> '
    tr += '<label class="checkbox-inline"><input type="checkbox" class="cmdAttr" data-l1key="isHistorized" checked/>{{Historiser}}</label> '
    tr += '<label class="checkbox-inline"><input type="checkbox" class="cmdAttr" data-l1key="display" data-l2key="invertBinary"/>{{Inverser}}</label> '
    tr += '<div style="margin-top:7px;">'
    tr += '<input class="tooltips cmdAttr form-control input-sm" data-l1key="configuration" data-l2key="minValue" placeholder="{{Min}}" title="{{Min}}" style="width:30%;max-width:80px;display:inline-block;margin-right:2px;">'
    tr += '<input class="tooltips cmdAttr form-control input-sm" data-l1key="configuration" data-l2key="maxValue" placeholder="{{Max}}" title="{{Max}}" style="width:30%;max-width:80px;display:inline-block;margin-right:2px;">'
    tr += '<input class="tooltips cmdAttr form-control input-sm" data-l1key="unite" placeholder="Unité" title="{{Unité}}" style="width:30%;max-width:80px;display:inline-block;margin-right:2px;">'
    tr += '<input class="tooltips cmdAttr form-control input-sm" data-l1key="configuration" data-l2key="listValue" placeholder="{{Liste de valeur|texte séparé par ;}}" title="{{Liste}}" style="margin-top : 5px;">';
    tr += '</div>'
    tr += '</td>'
    
    tr += '<td>';
    tr += '<span class="cmdAttr" data-l1key="htmlstate"></span>'; 
    tr += '</td>';    

tr += '<td>';
    if (is_numeric(_cmd.id)) {
        tr += '<a class="btn btn-default btn-xs cmdAction" data-action="configure"><i class="fas fa-cogs"></i></a> ';
        tr += '<a class="btn btn-default btn-xs cmdAction" data-action="test"><i class="fa fa-rss"></i> {{Tester}}</a>';
    }
    tr += '<i class="fa fa-minus-circle pull-right cmdAction cursor" data-action="remove"></i>';
    tr += '</td>';
    
    tr += '</tr>';
    $('#table_cmd tbody').append(tr);
    $('#table_cmd tbody tr').last().setValues(_cmd, '.cmdAttr');
    if (isset(_cmd.type)) {
      $('#table_cmd tbody tr:last .cmdAttr[data-l1key=type]').value(init(_cmd.type));
    }
    jeedom.cmd.changeType($('#table_cmd tbody tr').last(), init(_cmd.subType));
    var tr = $('#table_cmd tbody tr:last');
    jeedom.eqLogic.buildSelectCmd({
      id:  $('.eqLogicAttr[data-l1key=id]').value(),
      filter: {type: 'info'},
      error: function (error) {
        $('#div_alert').showAlert({message: error.message, level: 'danger'});
      },
      success: function (result) {
        tr.find('.cmdAttr[data-l1key=value]').append(result);
        tr.setValues(_cmd, '.cmdAttr');
        jeedom.cmd.changeType(tr, init(_cmd.subType));
        initTooltips();
      }
    });
}

$('#bt_updateInfo').off('click').on('click', function () {
  ip = $('.eqLogicAttr[data-l1key=configuration][data-l2key=ip]').value();
  jeedom.denonavr.getDescription({
        ip : ip,
        error: function (error) {
          $('#div_alert').showAlert({message: error.message, level: 'danger'});
        },
        success: function (data) {
          console.log(data);
          $('#div_alert').showAlert({message: "L'équiment a été trouvé", level: 'success',ttl:10000});
          if (data.serialNumber) {
            $('.eqLogicAttr[data-l1key=configuration][data-l2key=serial]').value(data.serialNumber);
          }
          if (data.friendlyName) {
            $('.eqLogicAttr[data-l1key=name]').value(data.friendlyName);
          }
          if (data.manufacturer) {
            $('.eqLogicAttr[data-l1key=configuration][data-l2key=manufacturer]').value(data.manufacturer);
          }          
        }
      });
});

$('#bt_createCommands').off('click').on('click', function () {
  id = $('.eqLogicAttr[data-l1key=id]').value();
  jeedom.denonavr.createCommands({
        id : id,
        error: function (error) {
          $('#div_alert').showAlert({message: error.message, level: 'danger'});
        },
        success: function (data) {
          $('#div_alert').showAlert({message: "Les commandes ont été créées", level: 'success',ttl:10000});
        }
      });
});
