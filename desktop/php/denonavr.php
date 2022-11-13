<?php
  if (!isConnect('admin')) {
    throw new Exception('{{401 - Accès non autorisé}}');
  }
  $plugin = plugin::byId('denonavr');
  sendVarToJS('eqType', $plugin->getId());
  $eqLogics = eqLogic::byType($plugin->getId());
?>

<div class="row row-overflow">
	<div class="col-xs-12 eqLogicThumbnailDisplay">
		<legend><i class="fas fa-cog"></i>  {{Gestion}}</legend>
		<div class="eqLogicThumbnailContainer">
			<div class="cursor eqLogicAction logoPrimary" data-action="add">
				<i class="fas fa-plus-circle"></i>
				<br />
				<span>{{Ajouter}}</span>
      </div>
      <div class="cursor eqLogicAction logoSecondary" data-action="gotoPluginConf">
				<i class="fas fa-wrench"></i>
				<br />
				<span>{{Configuration}}</span>
      </div>    
    </div>
		<legend><i class="fas fa-table"></i> {{Mes Equipements}}</legend>
		<input class="form-control" placeholder="{{Rechercher}}" id="in_searchEqlogic" />
		<div class="eqLogicThumbnailContainer">
			<?php
        foreach ($eqLogics as $eqLogic) {
          $opacity = ($eqLogic->getIsEnable()) ? '' : 'disableCard';
          echo '<div class="eqLogicDisplayCard cursor '.$opacity.'" data-eqLogic_id="' . $eqLogic->getId() . '">';
          echo '<img src="' . $plugin->getPathImgIcon() . '"/>';
          echo '<br>';
          echo '<span class="name">' . $eqLogic->getHumanName(true, true) . '</span>';
          echo '</div>';
        }
      ?>
    </div>
  </div>
	
	<div class="col-xs-12 eqLogic" style="display: none;">
		<div class="input-group pull-right" style="display:inline-flex">
			<span class="input-group-btn">
				<a class="btn btn-default btn-sm eqLogicAction roundedLeft" data-action="configure"><i class="fas fa-cogs"></i> {{Configuration avancée}}
          </a><a class="btn btn-default btn-sm eqLogicAction" data-action="copy"><i class="fas fa-copy"></i> {{Dupliquer}}
          </a><a class="btn btn-sm btn-success eqLogicAction" data-action="save"><i class="fas fa-check-circle"></i> {{Sauvegarder}}
        </a><a class="btn btn-danger btn-sm eqLogicAction roundedRight" data-action="remove"><i class="fas fa-minus-circle"></i> {{Supprimer}}</a>
      </span>
    </div>
		<ul class="nav nav-tabs" role="tablist">
			<li role="presentation"><a href="#" class="eqLogicAction" aria-controls="home" role="tab" data-toggle="tab" data-action="returnToThumbnailDisplay"><i class="fas fa-arrow-circle-left"></i></a></li>
			<li role="presentation" class="active"><a href="#eqlogictab" aria-controls="home" role="tab" data-toggle="tab"><i class="fas fa-tachometer-alt"></i> {{Equipement}}</a></li>
			<li role="presentation"><a href="#commandtab" aria-controls="profile" role="tab" data-toggle="tab"><i class="fas fa-list"></i> {{Commandes}}</a></li>
    </ul>
		<div class="tab-content" style="height:calc(100% - 50px);overflow:auto;overflow-x: hidden;">
			<div role="tabpanel" class="tab-pane active" id="eqlogictab">
				<form class="form-horizontal">
					<fieldset>
            <div class="col-lg-6">
							<legend><i class="fas fa-wrench"></i> {{Paramètres généraux}}</legend>
              <div class="form-group">
                <label class="col-sm-3 control-label">{{Nom de l'équipement}}</label>
                <div class="col-sm-3">
                  <input type="text" class="eqLogicAttr form-control" data-l1key="id" style="display : none;" />
                  <input type="text" class="eqLogicAttr form-control" data-l1key="name" placeholder="{{Nom de l'équipement denon}}"/>
                </div>
              </div>
              <div class="form-group">
                <label class="col-sm-3 control-label" >{{Objet parent}}</label>
                <div class="col-sm-3">
                  <select id="sel_object" class="eqLogicAttr form-control" data-l1key="object_id">
                    <option value="">{{Aucun}}</option>
                    <?php
                      $options = '';
                      foreach ((jeeObject::buildTree(null, false)) as $object) {
                        $options .= '<option value="' . $object->getId() . '">' . str_repeat('&nbsp;&nbsp;', $object->getConfiguration('parentNumber')) . $object->getName() . '</option>';
                      }
                      echo $options;
                    ?>
                  </select>
                </div>              
              </div> 
              <div class="form-group">
                <label class="col-sm-3 control-label">{{Catégorie}}</label>
                <div class="col-sm-9">
                  <?php
                    foreach (jeedom::getConfiguration('eqLogic:category') as $key => $value) {
                      echo '<label class="checkbox-inline">';
                      echo '<input type="checkbox" class="eqLogicAttr" data-l1key="category" data-l2key="' . $key . '" />' . $value['name'];
                      echo '</label>';
                    }
                  ?>
                </div>
              </div>
              <div class="form-group">
                <label class="col-sm-3 control-label"></label>
                <div class="col-sm-9">
                  <label class="checkbox-inline"><input type="checkbox" class="eqLogicAttr" data-l1key="isEnable" checked/>{{Activer}}</label>
                  <label class="checkbox-inline"><input type="checkbox" class="eqLogicAttr" data-l1key="isVisible" checked/>{{Visible}}</label>
                </div>
              </div>   
              
              <legend><i class="fas fa-cogs"></i> {{Paramètres spécifiques}}</legend>
              <div class="form-group">
                <label class="col-sm-3 control-label">{{IP}}</label>
                <div class="col-sm-3">
                  <input type="text" class="eqLogicAttr form-control" data-l1key="configuration" data-l2key="ip" />
                </div>
              </div>
              <div class="form-group">
                <label class="col-sm-3 control-label">{{Fabricant}}</label>
                <div class="col-sm-3">
                  <select class="eqLogicAttr form-control" data-l1key="configuration" data-l2key="manufacturer" >
                    <option value="Denon">{{Denon}}</option>
                    <option value="Marantz">{{Marantz}}</option>
                  </select>                
                </div>
              </div>
              
              <div class="form-group">
                <label class="col-sm-3 control-label">{{Numéro de série}}</label>
                <div class="col-sm-3">
                  <input type="text" class="eqLogicAttr form-control" data-l1key="configuration" data-l2key="serial" />
                </div>
              </div>              
              <div class="form-group">
                <label class="col-sm-3 control-label">{{Zone}}</label>
                <div class="col-sm-3">
                  <select type="text" class="eqLogicAttr form-control" data-l1key="configuration" data-l2key="zone" >
                    <option value="main">Principale</option>
                    <option value="2">2</option>
                    <option value="3">3</option>
                  </select>
                </div>
              </div>
              <div class="form-group">
                <label class="col-sm-3 control-label">{{API Mode}}</label>
                <div class="col-sm-3">
                  <select class="eqLogicAttr form-control" data-l1key="configuration" data-l2key="mode" >
                    <option value="">{{Standard}}</option>
                    <option value="H">{{Heos}}</option>
                  </select>
                </div>
              </div>
              <div class="form-group">
                <label class="col-sm-3 control-label">{{Démon}}</label>
                <div class="col-sm-3">
                  <input type="checkbox" class="eqLogicAttr" data-l1key="configuration" data-l2key="enableDaemon" />
                </div>
              </div>          
              
              <div class="form-group">
                <label class="col-sm-3 control-label"></label>
                <div class="col-sm-6">
                  <a id="bt_updateInfo" class="btn btn-primary"><i class="fas fa-wrench"></i> {{Interroge l'équipement}}</a>
                  <a id="bt_createCommands" class="btn btn-danger"><i class="fas fa-search"></i> {{Recréer les commandes}}</a>
                </div>
              </div>           
            </div>
          </fieldset>
        </form>
      </div>
			<div role="tabpanel" class="tab-pane" id="commandtab">
				<a class="btn btn-success btn-sm cmdAction pull-right" data-action="add" style="margin-top:5px;"><i class="fa fa-plus-circle"></i> {{Ajouter une Commande}}</a><br/><br/>
        
				<table id="table_cmd" class="table table-bordered table-condensed">
					<thead>
						<tr>
							<th style="width: 300px;">{{Nom}}</th>
              <th style="width: 130px;">{{Type}}</th>
              <th>{{Nom logique}}</th>
              <th>{{Catégorie}}</th>
              <th style="width: 300px;">{{Paramètres}}</th>
              <th>{{Etat}}</th>
              <th style="width: 150px;">{{Action}}</th>
            </tr>
          </thead>
					<tbody>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<?php include_file('core', 'denonavr', 'class.js', 'denonavr'); ?>
<?php include_file('desktop', 'denonavr', 'js', 'denonavr');?>
<?php include_file('core', 'plugin.template', 'js');?>
