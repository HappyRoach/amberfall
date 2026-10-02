using System.Linq;
using Content.Shared.Humanoid.Prototypes;
using Content.Shared.Preferences;

namespace Content.Client.Lobby.UI;

public sealed partial class HumanoidProfileEditor
{
    private readonly List<SpeciesChoice> _speciesChoices = new();
    private readonly List<SpeciesPrototype> _subspecies = new();

    private sealed record SpeciesChoice(
        string Name,
        SpeciesPrototype DefaultSpecies,
        List<SpeciesPrototype>? Subspecies = null);

    public void RefreshSpecies()
    {
        SpeciesButton.Clear();
        _speciesChoices.Clear();

        var available = _prototypeManager.EnumeratePrototypes<SpeciesPrototype>()
            .Where(species => species.RoundStart)
            .OrderBy(species => Loc.GetString(species.Name))
            .ToList();

        foreach (var group in available.GroupBy(species => species.Category))
        {
            if (group.Key is not { } categoryId || !_prototypeManager.TryIndex(categoryId, out var category))
            {
                foreach (var species in group)
                    _speciesChoices.Add(new SpeciesChoice(Loc.GetString(species.Name), species));

                continue;
            }

            var members = group.ToList();
            var defaultSpecies = members.FirstOrDefault(species => species.ID == category.DefaultSpecies.Id);
            if (defaultSpecies == null)
            {
                defaultSpecies = members[0];
                _sawmill.Warning($"Species category {category.ID} has no available default {category.DefaultSpecies}; using {defaultSpecies.ID}.");
            }

            _speciesChoices.Add(new SpeciesChoice(Loc.GetString(category.Name), defaultSpecies, members));
        }

        _speciesChoices.Sort((a, b) => StringComparer.CurrentCultureIgnoreCase.Compare(a.Name, b.Name));
        for (var i = 0; i < _speciesChoices.Count; i++)
            SpeciesButton.AddItem(_speciesChoices[i].Name, i);

        SpeciesButton.Disabled = available.Count == 0;

        if (Profile != null && available.Count > 0 && available.All(species => species.ID != Profile.Species.Id))
        {
            var fallback = available.FirstOrDefault(species => species.ID == HumanoidCharacterProfile.DefaultSpecies.Id)
                ?? available[0];
            SetSpecies(fallback.ID);
        }
        else
        {
            UpdateSpeciesSelectors();
        }
    }

    private void UpdateSpeciesSelectors()
    {
        SubspeciesButton.Clear();
        _subspecies.Clear();
        SubspeciesContainer.Visible = false;

        var selectedSpecies = (Profile?.Species ?? HumanoidCharacterProfile.DefaultSpecies).Id;
        for (var i = 0; i < _speciesChoices.Count; i++)
        {
            var choice = _speciesChoices[i];
            var containsSpecies = choice.Subspecies?.Any(species => species.ID == selectedSpecies)
                ?? choice.DefaultSpecies.ID == selectedSpecies;
            if (!containsSpecies)
                continue;

            SpeciesButton.SelectId(i);
            if (choice.Subspecies == null)
                return;

            _subspecies.AddRange(choice.Subspecies);
            SubspeciesContainer.Visible = true;
            for (var j = 0; j < _subspecies.Count; j++)
            {
                var species = _subspecies[j];
                SubspeciesButton.AddItem(Loc.GetString(species.Name), j);
                if (species.ID == selectedSpecies)
                    SubspeciesButton.SelectId(j);
            }

            return;
        }
    }
}
