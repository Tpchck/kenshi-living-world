// Спайк 1: независимая проверка файлов, записанных tools/kmod.py, библиотекой OpenConstructionSet 4.1.0.
// usage: OcsProbe <out.json> <file1> [file2 ...]
// Для каждого файла: читает OcsReader'ом, дампит сводку в JSON, перезаписывает OcsWriter'ом в <file>.ocs
// (чтобы kmod мог прочитать вывод OCS — проверка в обе стороны).
using System.Text.Json;
using OpenConstructionSet.Data;
using OpenConstructionSet.IO;

var outJson = args[0];
var result = new List<object>();

foreach (var path in args.Skip(1))
{
    DataFileData data;
    using (var reader = new OcsReader(File.ReadAllBytes(path)))
        data = reader.ReadDataFile();

    Console.WriteLine($"{Path.GetFileName(path)}: type={(int)data.Type} items={data.Items.Count} lastId={data.LastId} " +
                      $"deps=[{string.Join(",", data.Header?.Dependencies ?? [])}]");

    var items = data.Items.Select(i => new
    {
        sid = i.StringId,
        type = (int)i.Type,
        name = i.Name,
        change = (int)i.SaveData.ChangeType,
        nvalues = i.Values.Count,
        refs = i.ReferenceCategories.ToDictionary(c => c.Name, c => c.References.Count),
        deletedRefs = i.ReferenceCategories.SelectMany(c => c.References).Count(r => r.IsDeleted()),
        values = i.Values.ToDictionary(v => v.Key, v => v.Value.ToString()),
    }).ToList();
    result.Add(new { file = Path.GetFileName(path), items });

    using var fs = File.Create(path + ".ocs");
    using var writer = new OcsWriter(fs);
    writer.Write(data);
}

File.WriteAllText(outJson, JsonSerializer.Serialize(result, new JsonSerializerOptions
{
    WriteIndented = true,
    Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
}));
